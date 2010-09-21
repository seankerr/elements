# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import copy
import datetime
import new
import re

import settings

from elements.core.exception import ModelException

# ----------------------------------------------------------------------------------------------------------------------

class ModelMetaclass (type):

    def __init__ (cls, name, bases, members):
        """
        Create a new ModelMetaclass instance.

        @param cls     (class) The metaclass instance.
        @param name    (str)   The class name.
        @param bases   (tuple) The class base and interfaces.
        @param members (dict)  The class members.
        """

        if name == "Model" and ModelMetaclass.__module__ == cls.__module__:
            return type.__init__(cls, name, bases, members)

        if Model not in bases:
            raise ModelException("%s must sub-class Model in order to use Metaclass" % name)

        # meta details
        if not hasattr(cls, "Meta"):
            cls.Meta = new.classobj("Meta", (object,), {})

        if not hasattr(cls.Meta, "required") or type(cls.Meta.required) != bool:
            cls.Meta.required = True

        cls.Meta.default   = {}
        cls.Meta.fields    = {}
        cls.Meta.groups    = {}
        cls.Meta.read_only = []

        # iterate class instances
        for field_name in dir(cls):
            field_inst = getattr(cls, field_name)

            if not isinstance(field_inst, Field):
                continue

            field_inst.field = field_name
            field_inst.model = cls

            if field_inst.default is not None:
                cls.Meta.default[field_name] = field_inst.default

            if field_inst.read_only:
                field_inst.required = False

                cls.Meta.read_only.append(field_name)

            if field_inst.required is None:
                field_inst.required = cls.Meta.required

            if field_inst.group and field_inst.group not in cls.Meta.groups:
                if not hasattr(cls, "group_" + field_inst.group):
                    raise ModelException("%s is missing group validator group_%s()" % (name, field_inst.group))

                cls.Meta.groups[field_inst.group] = None

            cls.Meta.fields[field_name] = field_inst

            delattr(cls, field_name)

        return type.__init__(cls, name, bases, members)

# ----------------------------------------------------------------------------------------------------------------------

class Model:

    __metaclass__ = ModelMetaclass

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, *args, **kwargs):
        """
        Create a new Model instance.
        """

        self.__dict__["_errors"] = {}
        self.__dict__["_values"] = copy.copy(self.Meta.default)

        if len(kwargs) > 0:
            for key, value in kwargs.items():
                if key in self.Meta.fields:
                    self.__dict__["_values"][key] = value

    # ------------------------------------------------------------------------------------------------------------------

    def __contains__ (self, name):
        """
        Indicates that the model contains a field.

        @param name (str) The field name.

        @return (bool) True, upon success, otherwise False.
        """

        return name in self.Meta.fields

    # ------------------------------------------------------------------------------------------------------------------

    def __delattr__ (self, name):
        """
        Delete a field value.

        @param name (str) The field name.
        """

        self.__delitem__(name)

    # ------------------------------------------------------------------------------------------------------------------

    def __delitem__ (self, name):
        """
        Delete a field value.

        @param name (str) The field name.
        """

        if name not in self.Meta.fields:
            raise ModelException("%s does not contain field %s" % (self.__class__.__name__, name))

        if name in self.__dict__["_values"]:
            del self.__dict__["_values"][name]

    # ------------------------------------------------------------------------------------------------------------------

    def __getattr__ (self, name):
        """
        Retrieve a field value.

        @param name (str) The field name.

        @return (object) The field value.
        """

        return self.__getitem__(name)

    # ------------------------------------------------------------------------------------------------------------------

    def __getitem__ (self, name):
        """
        Retrieve a field value.

        @param name (str) The field name.

        @return (object) The field value.
        """

        if name in self.__dict__["_values"]:
            return self.__dict__["_values"][name]

        if name in self.Meta.fields:
            return None

        raise ModelException("%s does not contain field %s" % (self.__class__.__name__, name))

    # ------------------------------------------------------------------------------------------------------------------

    def __setattr__ (self, name, value):
        """
        Set a field value.

        @param name (str) The field name.
        """

        self.__setitem__(name, value)

    # ------------------------------------------------------------------------------------------------------------------

    def __setitem__ (self, name, value):
        """
        Set a field value.

        @param name (str) The field name.
        """

        if name not in self.Meta.fields:
            raise ModelException("%s does not contain field %s" % (self.__class__.__name__, name))

        self.__dict__["_values"][name] = value

    # ------------------------------------------------------------------------------------------------------------------

    def errors (self):
        """
        Retrieve all validation errors.

        @return (dict) Any errors that may have been set during validation.
        """

        return self.__dict__["_errors"]

    # ------------------------------------------------------------------------------------------------------------------

    def merge (self, *args, **kwargs):
        """
        Merge keyword arguments into the model values dict.
        """

        for key, value in kwargs.items():
            if key in self.Meta.fields:
                self.__dict__["_values"][key] = value

    # ------------------------------------------------------------------------------------------------------------------

    def validate (self):
        """
        Validate all model field values.

        @return (bool) True, if validation succeeded, otherwise False.
        """

        # validate groups
        for group in self.Meta.groups.keys():
            self.Meta.groups[group] = getattr(self, "group_" + group)()

        # validate fields
        for field_name, field_inst in self.Meta.fields.items():
            if field_name in self.__dict__["_values"]:
                res = field_inst.validate(self.__dict__["_values"][field_name])

                if res[0] == True:
                    self.__dict__["_values"][field_name] = res[1]

            else:
                res = field_inst.validate(None)

            if res[0] == False:
                self.__dict__["_errors"][field_name] = res[2]

        return len(self.__dict__["_errors"]) == 0

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def validate_field (cls, field, value):
        """
        Validate an individual field value.

        @param field (str)    The field to validate.
        @param value (object) The field value.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if field not in cls.Meta.fields:
            return (False, field, "Unknown field name")

        return cls.Meta.fields[field].validate(value)

    # ------------------------------------------------------------------------------------------------------------------

    def values (self):
        """
        Retrieve all model values.

        @return (dict) The field name/value pairs.
        """

        return self.__dict__["_values"]

# ----------------------------------------------------------------------------------------------------------------------

class FieldMetaclass (type):

    def __init__ (cls, name, bases, members):
        """
        Create a new FieldMetaclass instance.

        @param cls     (class) The metaclass instance.
        @param name    (str)   The class name.
        @param bases   (tuple) The class base and interfaces.
        @param members (dict)  The class members.
        """

        if name == "Field" and FieldMetaclass.__module__ == cls.__module__:
            return type.__init__(cls, name, bases, members)

        if not hasattr(cls, "type") or type(getattr(cls, "type")) != new.instancemethod:
            raise ModelException("Field sub-class '%s' is missing type() or it is not an instance method" % name)

        # add a Meta class
        cls.Meta = new.classobj("Meta", (object,), {})

        return type.__init__(cls, name, bases, members)

# ----------------------------------------------------------------------------------------------------------------------

class Field:

    __metaclass__ = FieldMetaclass

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Field instance.

        @param name (str) The proper field name.
        """

        self.default      = kwargs.get("default", None)
        self.field        = ""
        self.group        = kwargs.get("group", None)
        self.model        = None
        self.name         = name
        self.read_only    = kwargs.get("read_only", False)
        self.required     = kwargs.get("required", None)
        self.required_err = kwargs.get("required_err", settings.model_required_err)
        self.validators   = []

    # ------------------------------------------------------------------------------------------------------------------

    def error (self, message, value, validator):
        """
        Make necessary error message replacements.

        This replaces the following values:

        * %1 - The model field name.
        * %2 - The proper field name.
        * %3 - The validator.
        * %4 - The value.

        @param message   (str)    The error message.
        @param value     (object) The value.
        @param validator (str)    The validator against which the value was checked.

        @return (str) The formatted error message.
        """

        return message.replace("%1", self.field) \
                      .replace("%2", self.name) \
                      .replace("%3", validator) \
                      .replace("%4", value)

    # ------------------------------------------------------------------------------------------------------------------

    def validate (self, value):
        """
        Validate this field.

        @param value (object) The value to validate.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if value in (None, ""):
            if self.group and self.model.Meta.groups[self.group]:
                return (False, value, self.required_err)

            if self.required:
                return (False, value, self.required_err)

            return (True, value)

        res = self.type(value)

        if res[0] == False:
            return res

        value = res[1]

        if len(self.validators):
            for validator in self.validators:
                res = validator(value)

                if res[0] == False:
                    return res

                value = res[1]

            return res

        return (True, value)

# ----------------------------------------------------------------------------------------------------------------------

class Boolean (Field):

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Boolean instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_boolean_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if type(value) == bool:
            return (True, value)

        if type(value) == int:
            return (True, value > 0)

        if type(value) == str:
            value = value.lower()

            if value in ("yes", "true", "1"):
                return (True, True)

            if value in ("no", "false", "0"):
                return (True, False)

        error = self.error(self.type_err, value, "type bool")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Date (Field):

    _regex = re.compile("^(\d{4}(?P<sep1>-|/)\d{2}(?P=sep1)\d{2}|\d{2}(?P<sep2>-|/)\d{2}(?P=sep2)\d{4})$")

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Date instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_date_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            if type(value) == datetime.date:
                return (True, value)

            value = str(value)

            if self._regex.match(value):
                return (True, datetime.date(int(value[0:4]), int(value[5:7]), int(value[8:10])))

        except:
            pass

        error = self.error(self.type_err, value, "type date")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Datetime (Field):

    _regex = re.compile("^(\d{4}(?P<sep1>-|/)\d{2}(?P=sep1)\d{2}|\d{2}(?P<sep2>-|/)\d{2}(?P=sep2)\d{4}) \d{2}:\d{2}(" \
                        ":\d{2})?$")

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Datetime instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_datetime_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            if type(value) == datetime.datetime:
                return (True, value)

            value = str(value)

            if self._regex.match(value):
                if len(value) > 16:
                    return (True, datetime.datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]),
                                                    int(value[11:13]), int(value[14:16]), int(value[17:19])))

                return (True, datetime.datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]), int(value[11:13]),
                                                int(value[14:16])))

        except:
            pass

        error = self.error(self.type_err, value, "type datetime")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Domain (Field):

    _regex = re.compile("^([a-z0-9]([-a-z0-9]*[a-z0-9])?\\.)+((a[cdefgilmnoqrstuwxz]|aero|arpa)|(b[abdefghijmnorstvw" \
                        "yz]|biz)|(c[acdfghiklmnorsuvxyz]|cat|com|coop)|d[ejkmoz]|(e[ceghrstu]|edu)|f[ijkmor]|(g[abd" \
                        "efghilmnpqrstuwy]|gov)|h[kmnrtu]|(i[delmnoqrst]|info|int)|(j[emop]|jobs)|k[eghimnprwyz]|l[a" \
                        "bcikrstuvy]|(m[acdghklmnopqrstuvwxyz]|mil|mobi|museum)|(n[acefgilopruz]|name|net)|(om|org)|" \
                        "(p[aefghklmnrstwy]|pro)|qa|r[eouw]|s[abcdeghijklmnortvyz]|(t[cdfghjklmnoprtvwz]|travel)|u[a" \
                        "gkmsyz]|v[aceginu]|w[fs]|y[etu]|z[amw])$")

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Domain instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_domain_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            value = str(value)

            if self._regex.match(value):
                return (True, value)

        except:
            pass

        error = self.error(self.type_err, value, "type domain")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Email (Field):

    _regex = re.compile("^(?:[a-z0-9!\#$%*\/?|^{}`~&\'+=_.-]+|\"(?:(?:\\\\\\\\)*\\\\\"|[^\\\\\"]+)*\")@(?:(?:(?:25[0" \
                        "-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[a-z0" \
                        "-9]+)(?:[a-z0-9-]*[a-z0-9])*\.)+(?:arpa|com|edu|gov|int|mil|net|org|biz|info|name|pro|aero|" \
                        "coop|museum|travel|tel|mobi|jobs|[a-z]{2}))$")

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Email instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_email_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            value = str(value)

            if self._regex.match(value):
                return (True, value)

        except:
            pass

        error = self.error(self.type_err, value, "type email")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Float (Field):

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Float instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_float_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

        # min size validator
        if "min" in kwargs and kwargs["min"]:
            self.min_val = kwargs["min"]

            if type(self.min_val) in (int, float):
                self.min_err = kwargs.get("min_err", settings.model_float_min_err)

                self.validators.append(self.min_check)

            else:
                raise ModelException("%s has invalid min validator: %s" % (self.__class__.__name__, self.min_val))

        # max size validator
        if "max" in kwargs and kwargs["max"]:
            self.max_val = kwargs["max"]

            if type(self.max_val) in (int, float):
                self.max_err = kwargs.get("max_err", settings.model_float_max_err)

                self.validators.append(self.max_check)

            else:
                raise ModelException("%s has invalid max validator: %s" % (self.__class__.__name__, self.max_val))

    # ------------------------------------------------------------------------------------------------------------------

    def max_check (self, value):
        """
        Check the maximum size of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if value > self.max_val:
            return (False, value, self.error(self.max_err, str(value), str(self.max_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def min_check (self, value):
        """
        Check the minimum size of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if value < self.min_val:
            return (False, value, self.error(self.min_err, str(value), str(self.min_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            return (True, float(value))

        except:
            error = self.error(self.type_err, value, "type float")

            return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Int (Field):

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Int instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_int_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

        # min size validator
        if "min" in kwargs and kwargs["min"]:
            self.min_val = kwargs["min"]

            if type(self.min_val) == int:
                self.min_err = kwargs.get("min_err", settings.model_int_min_err)

                self.validators.append(self.min_check)

            else:
                raise ModelException("%s has invalid min validator: %s" % (self.__class__.__name__, self.min_val))

        # max size validator
        if "max" in kwargs and kwargs["max"]:
            self.max_val = kwargs["max"]

            if type(self.max_val) == int:
                self.max_err = kwargs.get("max_err", settings.model_int_max_err)

                self.validators.append(self.max_check)

            else:
                raise ModelException("%s has invalid max validator: %s" % (self.__class__.__name__, self.max_val))

    # ------------------------------------------------------------------------------------------------------------------

    def max_check (self, value):
        """
        Check the maximum size of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if value > self.max_val:
            return (False, value, self.error(self.max_err, str(value), str(self.max_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def min_check (self, value):
        """
        Check the minimum size of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if value < self.min_val:
            return (False, value, self.error(self.min_err, str(value), str(self.min_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            return (True, int(value))

        except:
            error = self.error(self.type_err, value, "type int")

            return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class IPAddress (Field):

    _regex = "(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new IPAddress instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_ipaddress_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            value = str(value)

            if self._regex.match(value):
                return (True, value)

        except:
            pass

        error = self.error(self.type_err, value, "type ip address")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Money (Float):

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Money instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_money_type_err)

        if "min" in kwargs and "min_err" not in kwargs:
            self.min_err = settings.model_money_min_err

        if "max" in kwargs and "max_err" not in kwargs:
            self.max_err = settings.model_money_max_err

        # init parent class
        Float.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            value = float(value)

            return (True, float("%.2f" % (value + 0.001)))

        except:
            error = self.error(self.type_err, value, "type money")

            return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Text (Field):

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Text instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_text_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

        # min length validator
        if "min" in kwargs and kwargs["min"]:
            self.min_val = kwargs["min"]

            if type(self.min_val) == int:
                self.min_err = kwargs.get("min_err", settings.model_text_min_err)

                self.validators.append(self.min_check)

            else:
                raise ModelException("%s has invalid min validator: %s" % (self.__class__.__name__, self.min_val))

        # max length validator
        if "max" in kwargs and kwargs["max"]:
            self.max_val = kwargs["max"]

            if type(self.max_val) == int:
                self.max_err = kwargs.get("max_err", settings.model_text_max_err)

                self.validators.append(self.max_check)

            else:
                raise ModelException("%s has invalid max validator: %s" % (self.__class__.__name__, self.max_val))

        # regex validator
        if "regex" in kwargs and kwargs["regex"]:
            self.regex_val = kwargs["regex"]

            if type(self.regex_val) == str:
                self.regex_err = kwargs.get("regex_err", settings.model_text_regex_err)

                try:
                    self.regex_val = re.compile(self.regex_val)

                except Exception, e:
                    raise ModelException("%s has invalid regex pattern: %s" % (self.__class__.__name__, str(e)))

                self.validators.append(self.regex_check)

            else:
                raise ModelException("%s has invalid regex validator: %s" % (self.__class__.__name__,
                                                                             str(self.regex_val)))

    # ------------------------------------------------------------------------------------------------------------------

    def max_check (self, value):
        """
        Check the maximum length of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if len(value) > self.max_val:
            return (False, value, self.error(self.max_err, value, str(self.max_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def min_check (self, value):
        """
        Check the minimum length of the value.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if len(value) < self.min_val:
            return (False, value, self.error(self.min_err, value, str(self.min_val)))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def regex_check (self, value):
        """
        Check the value against a pattern.

        @param value (object) The value to check.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if not self.regex_val.search(value):
            return (False, value, self.error(self.regex_err, value, self.regex_val.pattern))

        return (True, value)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            return (True, str(value))

        except:
            error = self.error(self.type_err, value, "type str")

            return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class Time (Field):

    _regex = re.compile("^\d{2}:\d{2}(:\d{2})?$")

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new Time instance.

        @param name (str) The proper field name.
        """

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_time_type_err)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            if type(value) == datetime.time:
                return (True, value)

            value = str(value)

            if self._regex.match(value):
                if len(value) > 5:
                    return (True, datetime.time(int(value[0:2]), int(value[3:5]), int(value[6:8])))

                return (True, datetime.time(int(value[0:2]), int(value[3:5])))

        except:
            pass

        error = self.error(self.type_err, value, "type time")

        return (False, value, error)

# ----------------------------------------------------------------------------------------------------------------------

class URL (Field):

    _regex = "://([a-z0-9]([-a-z0-9]*[a-z0-9])?\\.)+((a[cdefgilmnoqrstuwxz]|aero|arpa)|(b[abdefghijmnorstvwyz]|biz)|" \
             "(c[acdfghiklmnorsuvxyz]|cat|com|coop)|d[ejkmoz]|(e[ceghrstu]|edu)|f[ijkmor]|(g[abdefghilmnpqrstuwy]|go" \
             "v)|h[kmnrtu]|(i[delmnoqrst]|info|int)|(j[emop]|jobs)|k[eghimnprwyz]|l[abcikrstuvy]|(m[acdghklmnopqrstu" \
             "vwxyz]|mil|mobi|museum)|(n[acefgilopruz]|name|net)|(om|org)|(p[aefghklmnrstwy]|pro)|qa|r[eouw]|s[abcde" \
             "ghijklmnortvyz]|(t[cdfghjklmnoprtvwz]|travel)|u[agkmsyz]|v[aceginu]|w[fs]|y[etu]|z[amw])(/[\\x20-\\x7E" \
             "]+)?$"

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, name, *args, **kwargs):
        """
        Create a new URL instance.

        @param name (str) The proper field name.
        """

        protocols = ("http",)

        # type validator
        self.type_err = kwargs.get("type_err", settings.model_url_type_err)

        # check for protocols
        if "protocols" in kwargs:
            protocols = kwargs["protocols"]

            if type(protocols) != tuple:
                protocols = (protocol,)

        # compile custom pattern
        self.regex = re.compile("^(" + "|".join(protocols).lower() + ")" + self._regex)

        # init parent class
        Field.__init__(self, name, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def type (self, value):
        """
        Make all attempts to convert the value to the proper type.

        @param value (object) The value to type test.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        try:
            value = str(value)

            if self.regex.match(value.lower()):
                return (True, value)

        except:
            pass

        error = self.error(self.type_err, value, "type url")

        return (False, value, error)
