import logging
from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from DeviceManager.DatabaseModels import db
from DeviceManager.DatabaseModels import handle_consistency_exception, assert_template_exists
from DeviceManager.DatabaseModels import DeviceTemplate, DeviceAttr, DeviceTemplateMap
from DeviceManager.SerializationModels import *
from DeviceManager.TenancyManager import init_tenant_context
from DeviceManager.KafkaNotifier import send_raw, DeviceEvent

from DeviceManager.app import app
from DeviceManager.utils import *

LOGGER = logging.getLogger('device-manager.' + __name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)

template = Blueprint('template', __name__)


def attr_format(req, result):
    """ formats output attr list acording to user input """
    attrs_format = req.args.get('attr_format', 'both')

    def remove(d,k):
        try:
            LOGGER.info('will remove {}'.format(k))
            d.pop(k)
        except KeyError:
            pass

    if attrs_format == 'split':
        remove(result, 'attrs')
    elif attrs_format == 'single':
        remove(result, 'config_attrs')
        remove(result, 'data_attrs')

    return result


class TemplateHandler:

    def __init__(self):
        pass

    @staticmethod
    def get_templates(req):
        """
        Fetches known templates, potentially limited by a given value. Ordering
        might be user-configurable too.

        :param req: The received HTTP request, as created by Flask.
        :return A JSON containing pagination information and the template list
        :rtype JSON
        :raises HTTPRequestError: If no authorization token was provided (no
        tenant was informed)
        """
        init_tenant_context(req, db)

        page_number, per_page = get_pagination(req)
        page = DeviceTemplate.query.paginate(page=int(page_number),
                                             per_page=int(per_page),
                                             error_out=False)
        templates = list(map(lambda x: attr_format(req, x), template_list_schema.dump(page.items).data))
        result = {
            'pagination': {
                'page': page.page,
                'total': page.pages,
                'has_next': page.has_next,
                'next_page': page.next_num
            },
            'templates': templates
        }

        return result

    @staticmethod
    def create_template(req):
        """
        Creates a new template.

        :param req: The received HTTP request, as created by Flask.
        :return The created template.
        :raises HTTPRequestError: If no authorization token was provided (no
        tenant was informed)
        :raises HTTPRequestError: If template attribute constraints were
        violated. This might happen if two attributes have the same name, for
        instance.
        """
        init_tenant_context(req, db)
        tpl, json_payload = parse_payload(req, template_schema)
        LOGGER.info(tpl)
        loaded_template = DeviceTemplate(**tpl)
        load_attrs(json_payload['attrs'], loaded_template, DeviceAttr, db)
        db.session.add(loaded_template)

        try:
            db.session.commit()
        except IntegrityError:
            raise HTTPRequestError(400, 'Template attribute constraints are \
                violated by the request')

        results = {
            'template': template_schema.dump(loaded_template).data,
            'result': 'ok'
        }
        return results

    @staticmethod
    def get_template(req, template_id):
        """
        Fetches a single template.
        :param req: The received HTTP request, as created by Flask.
        :param template_id: The requested template ID.
        :return A Template
        :rtype Template, as described in DatabaseModels package
        :raises HTTPRequestError: If no authorization token was provided (no
        tenant was informed)
        :raises HTTPRequestError: If this template could not be found in
        database.
        """
        init_tenant_context(req, db)
        tpl = assert_template_exists(template_id)
        json_template = template_schema.dump(tpl).data
        attr_format(req, json_template)
        return json_template

    @staticmethod
    def remove_template(req, template_id):
        """
        Deletes a single template.

        :param req: The received HTTP request, as created by Flask.
        :param template_id: The template to be removed.
        :return The removed template.
        :rtype JSON
        :raises HTTPRequestError: If no authorization token was provided (no
        tenant was informed)
        :raises HTTPRequestError: If this template could not be found in
        database.
        :raises HTTPRequestError: If the template is being currently used by
        a device.
        """
        init_tenant_context(req, db)
        tpl = assert_template_exists(template_id)

        json_template = template_schema.dump(tpl).data
        try:
            db.session.delete(tpl)
            db.session.commit()
        except IntegrityError:
            raise HTTPRequestError(400, "Template cannot be removed as it is \
                    being used by devices")

        results = {
            'result': 'ok',
            'removed': json_template
        }

        return results

    @staticmethod
    def update_template(req, template_id):
        """
        Updates a single template.

        :param req: The received HTTP request, as created by Flask.
        :param template_id: The template to be updated.
        :return The old version of this template (previous to the update).
        :rtype JSON
        :raises HTTPRequestError: If no authorization token was provided (no
        tenant was informed)
        :raises HTTPRequestError: If this template could not be found in
        database.
        """
        service = init_tenant_context(req, db)

        # find old version of the template, if any
        old = assert_template_exists(template_id)
        # parse updated version from payload
        updated, json_payload = parse_payload(req, template_schema)
        old.label = updated['label']

        new = json_payload['attrs']
        for a in old.attrs:
            found = False
            for idx, b in enumerate(new):
                if (a.label == b['label']) and (a.type == b['type']):
                    found = True
                    a.value_type = b.get('value_type', None)
                    a.static_value = b.get('static_value', None)
                    new.pop(idx)
                    break
            if not found:
                db.session.delete(a)

        for a in new:
            db.session.add(DeviceAttr(template=old, **a))


        try:
            db.session.commit()
        except IntegrityError as error:
            handle_consistency_exception(error)

        # notify interested parties that a set of devices might have been implicitly updated
        affected = db.session.query(DeviceTemplateMap) \
                             .filter(DeviceTemplateMap.template_id==template_id) \
                             .all()

        affected_devices = []
        for device in affected:
            affected_devices.append(device.device_id)

        event = {
            "event": DeviceEvent.TEMPLATE,
            "data": {
                "affected": affected_devices,
                "template": template_schema.dump(old).data
            },
            "meta": {"service": service}
        }
        send_raw(event, service)

        results = {
            'updated': template_schema.dump(old).data,
            'result': 'ok'
        }
        return results


@template.route('/template', methods=['GET'])
def flask_get_templates():
    try:
        result = TemplateHandler.get_templates(request)
        resp = make_response(json.dumps(result), 200)
        resp.mimetype = "application/json"
        return resp

    except ValidationError as e:
        results = {'message': 'failed to parse attr', 'errors': e}
        return make_response(json.dumps(results), 500)

    except HTTPRequestError as e:
        if isinstance(e.message, dict):
            return make_response(json.dumps(e.message), e.error_code)
        else:
            return format_response(e.error_code, e.message)


@template.route('/template', methods=['POST'])
def flask_create_template():
    try:
        result = TemplateHandler.create_template(request)
        resp = make_response(json.dumps(result), 200)
        resp.mimetype = "application/json"
        return resp

    except ValidationError as e:
        results = {'message': 'failed to parse attr', 'errors': e}
        return make_response(json.dumps(results), 400)
    except HTTPRequestError as error:
        if isinstance(error.message, dict):
            return make_response(json.dumps(error.message), error.error_code)
        else:
            return format_response(error.error_code, error.message)


@template.route('/template/<template_id>', methods=['GET'])
def flask_get_template(template_id):
    try:
        result = TemplateHandler.get_template(request, template_id)
        resp = make_response(json.dumps(result), 200)
        resp.mimetype = "application/json"
        return resp
    except ValidationError as e:
        results = {'message': 'failed to parse attr', 'errors': e}
        return make_response(json.dumps(results), 500)
    except HTTPRequestError as e:
        if isinstance(e.message, dict):
            return make_response(json.dumps(e.message), e.error_code)
        else:
            return format_response(e.error_code, e.message)


@template.route('/template/<template_id>', methods=['DELETE'])
def flask_remove_template(template_id):
    try:
        result = TemplateHandler.remove_template(request, template_id)
        resp = make_response(json.dumps(result), 200)
        resp.mimetype = "application/json"
        return resp
    except ValidationError as e:
        results = {'message': 'failed to parse attr', 'errors': e}
        return make_response(json.dumps(results), 500)
    except HTTPRequestError as e:
        if isinstance(e.message, dict):
            return make_response(json.dumps(e.message), e.error_code)
        else:
            return format_response(e.error_code, e.message)


@template.route('/template/<template_id>', methods=['PUT'])
def flask_update_template(template_id):
    try:
        result = TemplateHandler.update_template(request, template_id)
        resp = make_response(json.dumps(result), 200)
        resp.mimetype = "application/json"
        return resp
    except ValidationError as e:
        results = {'message': 'failed to parse attr', 'errors': e}
        return make_response(json.dumps(results), 500)
    except HTTPRequestError as error:
        if isinstance(error.message, dict):
            return make_response(json.dumps(error.message), error.error_code)
        else:
            return format_response(error.error_code, error.message)


app.register_blueprint(template)
