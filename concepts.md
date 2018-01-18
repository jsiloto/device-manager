# DeviceManager concepts

Here are the main concepts needed to correctly use DeviceManager. They are not hard to understand, but they are essential to operate not only DeviceManager, but the dojot platform as well.

## Device

In dojot, a device is a digital representation of an actual device or gateway with one or more sensors or of a virtual one with sensors/attributes inferred from other devices.

Consider, for instance, an actual device with temperature and humidity sensors; it can be represented into dojot as a device with two attributes (one for each sensor). We call this kind of device as regular device or by its communication protocol, for instance, MQTT device or CoAP device.

We can also create devices which don’t directly correspond to their actual ones, for instance, we can create one with higher level of information of temperature (is becoming hotter or is becoming colder) whose values are inferred from temperature sensors of other devices. This kind of device is called virtual device.

The information model used for both "real" and virtual devices is as following:

- Device:
  - id (string, read-only): this is the identifier that will be used when referring to this device
  - label (string, read-write, required): an user label to identify this device more easily
  - created (DateTime, read-only): device creation date
  - updated (DateTime, read-only): device update date
  - templates ([ string (template ID) ], read-write): list of template IDs to "assemble" this device (more on this on 'Template' section)
  - attrs ([ Attributes ], read-only): list of attributes currently set to this device.

- Attributes:
  - id (integer, read-write): attribute ID (automatically generated**)
  - label (string, read-write, required): user label for this attribute
  - created (DateTime, read-only): attribute creation date
  - updated (DateTime, read-only): attribute update date
  - type (string, read-write, required): attribute type ("static" or "dynamic")
  - value_type (string, read-write, required): attribute value type ("string", "float", "integer", "geo")
  - static_value (string, read-write): if this is a static attribute, which is its static value
  - template_id (string, read-write): from which template did this attribute come from.

*although the code allows the user to set this.

## Template

All devices are created based on a *template*, which can be thought as a model of a device. As "model" we could think of part numbers or product models - one *prototype* from which devices are created. Templates in dojot have one label (any alphanumeric sequence), a list of attributes which will hold all the device emitted information, and optionally a few special attributes which will indicate how the device communicates, including transmission methods (protocol, ports, etc.) and message formats.

In fact, templates can represent not only "device models", but it can also abstract a "class of devices". For instance, we could have one template to represent all themometers that will be used in dojot. This template would have only one attribute called, let's say, "temperature". While creating the device, the user would select its "physical template", let's say *TexasInstr882*, and the 'thermometer' template. The user would have also to add translation instructions in order to map the temperature reading that will be sent from the device to a "temperature" attribute. 

In order to create a device, a user selects which templates are going to compose this new device. All their attributes are merged together and associated to it - they are tightly linked to the original template so that any template update will reflect all associated devices.

The information model used for templates is:

- Template:
  - id (string, read-write  ): this is the identifier that will be used when referring to this template
  - label (string, read-write, required): an user label to identify this template more easily
  - created (DateTime, read-only): template creation date
  - updated (DateTime, read-only): template update date
  - attrs ([ Attributes ], read-write): list of attributes currently set to this template - it's the same as attributes from Device section.

## APIs

You can check the documentation for all APIs exposed by DeviceManager [here](apis.html)

[BACK](./index.md)