# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import copy
import new

import settings

from DBUtils.PooledDB import PooledDB

from elements.core.exception import DatabaseModelException
from elements.core.exception import ModelException
from elements.model.model    import Int

# ----------------------------------------------------------------------------------------------------------------------

def get_connection (name="default"):
    """
    Retrieve a database connection.

    @param name (str) The database connection pool name.

    @return (object) A database connection.
    """

    if name not in settings.databases:
        raise DatabaseModelException("Non-existent database connection pool name %s" % name)

    return settings.databases[name]["instance"].connection()

# ----------------------------------------------------------------------------------------------------------------------

def init ():
    """
    Initialize database connection pools.

    Note: This will be called automatically when a DatabaseModel sub-class is present. Otherwise this must be called once at
          application startup.
    """

    try:
        for name, data in settings.databases.items():
            data = copy.copy(data)

            if "api" not in data:
                raise DatabaseModelException("Database %s is missing api setting" % name)

            if "pool" not in data:
                raise DatabaseModelException("Database %s is missing pool setting" % name)

            api  = data["api"]
            pool = data["pool"]

            del data["api"]
            del data["pool"]

            settings.databases[name]["instance"] = PooledDB(api, pool, **data)

    except Exception, e:
        raise DatabaseModelException(str(e))

# ----------------------------------------------------------------------------------------------------------------------

class DatabaseModelMetaclass (type):

    # indicates whether or not the pool has been initialized
    __POOL_INIT = False

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (cls, name, bases, members):
        """
        Create a new DatabaseModelMetaclass instance.
        
        @param cls     (class) The metaclass instance.
        @param name    (str)   The class name.
        @param bases   (tuple) The class base and interfaces.
        @param members (dict)  The class members.
        """

        if name == "DatabaseModel" and DatabaseModelMetaclass.__module__ == cls.__module__:
            return type.__init__(cls, name, bases, members)

        if not hasattr(cls, "model"):
            raise DatabaseModelException("%s is missing model property" % name)

        if not hasattr(cls, "table"):
            raise DatabaseModelException("%s is missing table property" % name)

        if not hasattr(cls, "primary_key"):
            cls.primary_key = cls.table + "_id"

        # meta details
        cls.Meta              = new.classobj("Meta", (object,), { "connection": None })
        cls.Meta.columns      = []
        cls.Meta.model        = cls.model
        cls.Meta.foreign_keys = {}
        cls.Meta.primary_key  = cls.primary_key
        cls.Meta.table        = cls.table

        del cls.model
        del cls.primary_key
        del cls.table

        # check foreign keys
        if hasattr(cls, "foreign_keys"):
            for field_name, model in cls.foreign_keys.items():
                if field_name not in cls.Meta.model.Meta.fields:
                    raise DatabaseModelException("%s does contain field %s" % (cls.Meta.model.__name__, field_name))

                if not isinstance(model(), DatabaseModel):
                    raise DatabaseModelException("%s is not a sub-class of DatabaseModel" % model.__name__)

                cls.Meta.foreign_keys[field_name] = model

            del cls.foreign_keys

        # check database pool
        if not DatabaseModelMetaclass.__POOL_INIT:
            init()
            
            DatabaseModelMetaclass.__POOL_INIT = True

        if hasattr(cls, "database"):
            if cls.database not in settings.databases:
                raise DatabaseModelException("%s uses nonexistent database %s" % (name, cls.database))

            cls.Meta.database = cls.database

            del cls.database

        else:
            if "default" not in settings.databases:
                raise DatabaseModelException("%s uses the default database, but it has not been specified" % name)

            cls.Meta.database = "default"

        cls.Meta.db = settings.databases[cls.Meta.database]["instance"]
        
        # check primary key
        if type(cls.Meta.primary_key) != str:
            raise DatabaseModelException("%s has an invalid primary key" % name)

        if cls.Meta.primary_key not in cls.Meta.model.Meta.fields:
            raise DatabaseModelException("%s primary key field '%s' does not exist in %s" % (name, cls.Meta.primary_key,
                                                                                             cls.Meta.model.__name__))

        if not isinstance(cls.Meta.model.Meta.fields[cls.Meta.primary_key], Int):
            raise DatabaseModelException("%s primary key field '%s' is not an integer field" % (name,
                                                                                                cls.Meta.primary_key))

        # get column details
        try:
            connection = None
            cursor     = None
            connection = cls.Meta.db.connection()
            cursor     = connection.cursor()

            cursor.execute("SELECT * FROM \"%s\" LIMIT 1" % cls.Meta.table)

            [cls.Meta.columns.append(column[0]) for column in cursor.description]

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

        return type.__init__(cls, name, bases, members)

# ----------------------------------------------------------------------------------------------------------------------

class DatabaseModel:

    __metaclass__ = DatabaseModelMetaclass

    # ------------------------------------------------------------------------------------------------------------------

    def __init__ (self, *args, **kwargs):
        """
        Create a new DatabaseModel instance.
        """

        self.__dict__["_connection"] = None
        self.__dict__["_model_inst"] = self.Meta.model(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def __contains__ (self, name):
        """
        Indicates that the model contains a field.

        @param name (str) The field name.

        @return (bool) True, upon success, otherwise False.
        """

        return name in self.__dict__["_model_inst"]

    # ------------------------------------------------------------------------------------------------------------------

    def __delattr__ (self, name):
        """
        Delete a field value.

        @param name (str) The field name.
        """

        del self.__dict__["_model_inst"][name]

    # ------------------------------------------------------------------------------------------------------------------

    def __delitem__ (self, name):
        """
        Delete a field value.

        @param name (str) The field name.
        """

        del self.__dict__["_model_inst"][name]

    # ------------------------------------------------------------------------------------------------------------------

    def __getattr__ (self, name):
        """
        Retrieve a field value.

        @param name (str) The field name.
        
        @return (object) The field value.
        """

        return self.__dict__["_model_inst"][name]

    # ------------------------------------------------------------------------------------------------------------------

    def __getitem__ (self, name):
        """
        Retrieve a field value.

        @param name (str) The field name.
        
        @return (object) The field value.
        """

        return self.__dict__["_model_inst"][name]

    # ------------------------------------------------------------------------------------------------------------------

    def __setattr__ (self, name, value):
        """
        Set a field value.

        @param name  (str)    The field name.
        @param value (object) The field value.
        """

        self.__dict__["_model_inst"][name] = value

    # ------------------------------------------------------------------------------------------------------------------

    def __setitem__ (self, name, value):
        """
        Set a field value.

        @param name  (str)    The field name.
        @param value (object) The field value.
        """

        self.__dict__["_model_inst"][name] = value

    # ------------------------------------------------------------------------------------------------------------------

    def delete (self):
        """
        Delete the record from the database that is associated with the primary key in this model.

        @return (bool) True, upon success, otherwise False.
        """

        meta   = self.Meta
        values = self.values()

        if meta.primary_key not in values:
            raise DatabaseModelException("This DatabaseModel instance does not represent an active database record")

        try:
            if self.__dict__["_connection"]:
                close      = False
                cursor     = None
                connection = self.__dict__["_connection"]

            else:
                close      = True
                cursor     = None
                connection = settings.databases[meta.database]["instance"].connection()

            cursor = connection.cursor()

            cursor.execute("DELETE FROM \"" + meta.table + "\" WHERE " + meta.primary_key + " = %s",
                           (values[meta.primary_key],))

            return cursor.rowcount and cursor.rowcount > 0

        except Exception, e:
            raise DatabaseModelException(str(e))

        finally:
            if cursor:
                cursor.close()

            if close and connection:
                connection.commit()
                connection.close()

    # ------------------------------------------------------------------------------------------------------------------

    def errors (self):
        """
        Retrieve all validation errors.

        @return (dict) The validation error key/value pairs.
        """

        return self.__dict__["_model_inst"].errors()

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def filter (cls, filters, query_type="AND"):
        """
        Retrieve a list of filtered records for this model.

        @param filters    (tuple) The tuple or list consisting of tuples or lists of column, operator and value entries.
        @param query_type (str)   The type of filtering, either AND or OR.
        """

        return DatabaseModelQuery(cls, filters, query_type)

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def get (cls, id, connection=None):
        """
        Retrieve a database record for this model.

        @param id         (int)    The primary key value.
        @param connection (object) The connection to use for this operation.
        """

        meta = cls.Meta

        try:
            if connection:
                close  = False
                cursor = None

            else:
                close      = True
                cursor     = None
                connection = settings.databases[meta.database]["instance"].connection()

            cursor = connection.cursor()

            cursor.execute("SELECT * FROM \"" + meta.table + "\" WHERE " + meta.primary_key + " = %s", (id,))

            record = cursor.fetchone()

            if record:
                record = cls(**dict(zip(meta.columns, record)))

                if not close:
                    # give the passed connection to the object as well
                    record.connection(connection)

            return record

        except Exception, e:
            raise DatabaseModelException(str(e))

        finally:
            if cursor:
                cursor.close()

            if close and connection:
                connection.close()

    # ------------------------------------------------------------------------------------------------------------------

    def get_connection (self, connection):
        """
        Retrieve the current connection that is used in this model.
        
        @return (object) The live database connection, if set_connection() has assigned a connection, otherwise None.
        """

        return self.__dict__["_connection"]

    # ------------------------------------------------------------------------------------------------------------------

    def save (self):
        """
        Save the record in the database that is associated with the primary key in this model, and if no primary key
        is set than create a new record.

        @return (bool) True, upon success.
        """

        meta = self.Meta

        try:
            if self.__dict__["_connection"]:
                close      = False
                cursor     = None
                connection = self.__dict__["_connection"]

            else:
                close      = True
                cursor     = None
                connection = settings.databases[meta.database]["instance"].connection()

            cursor = connection.cursor()
            values = self.values()

            if meta.primary_key in values:
                # update
                up_keys   = []
                up_values = []

                for key, value in values.items():
                    if key == meta.primary_key or key in meta.model.Meta.read_only:
                        continue

                    up_keys.append(key + "=%s")
                    up_values.append(value)

                up_values.append(values[meta.primary_key])

                cursor.execute("UPDATE \"" + meta.table + "\" SET " + ",".join(up_keys) + " WHERE " + \
                               meta.primary_key + " = %s", up_values)

            else:
                # insert
                in_fields = []
                in_keys   = []
                in_values = []

                for key, value in values.items():
                    if key in meta.model.Meta.read_only:
                        continue

                    in_fields.append("%s")
                    in_keys.append(key)
                    in_values.append(value)

                cursor.execute("INSERT INTO \"" + meta.table + "\" (" + ",".join(in_keys) + ") VALUES (" + \
                               ",".join(in_fields) + ")", in_values)

            return cursor.rowcount and cursor.rowcount > 0

        except Exception, e:
            raise DatabaseModelException(str(e))

        finally:
            if cursor:
                cursor.close()

            if close and connection:
                connection.commit()
                connection.close()

    # ------------------------------------------------------------------------------------------------------------------

    def set_connection (self, connection):
        """
        Set the current connection that will be used in this model.

        Note: Once a connection is passed it is the responsibility of the caller to close the connection.

        @param connection (object) The database connection.
        """

        self.__dict__["_connection"] = connection

    # ------------------------------------------------------------------------------------------------------------------

    def validate (self, validate_keys=True):
        """
        Validate all model field values.

        @param validate_keys (bool) Indicates that all foreign keys will be verified for existence.

        @return (bool) True, upon success, otherwise False.
        """

        meta      = self.Meta
        model     = self.__dict__["_model_inst"]
        validated = model.validate()

        if not validated:
            # get the validation errors and if the length of them is one and the error is from the primary key,
            # do a check for the value and if it is None, then we know the error was a required error, which can be
            # omitted since it's a primary key
            errors = model.errors()

            if len(errors) == 1 and meta.primary_key in errors and getattr(model, meta.primary_key) == None:
                validated = True

                # remove the primary key error
                del errors[meta.primary_key]

        if validated:
            # check foreign key values
            if not validate_keys or len(meta.foreign_keys) == 0:
                return True

            try:
                if self.__dict__["_connection"]:
                    close      = False
                    connection = self.__dict__["_connection"]

                else:
                    close      = True
                    connection = settings.databases[meta.database]["instance"].connection()

                values = self.values()

                for key, model in meta.foreign_keys.items():
                    if key in values:
                        if not model.get(values[key], connection=connection):
                            errors[key] = settings.dbmodel_fk_constraint_err

                return len(errors) == 0

            except Exception, e:
                raise DatabaseModelException(str(e))

            finally:
                if close and connection:
                    connection.close()

        return False

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def validate_field (cls, field, value):
        """
        Validate an individual field value.

        @param field (str)    The specified field to validate.
        @param value (object) The value to validate.

        @return (tuple) Upon success a two-part tuple where the first part is True and the second part is the field
                        value. Upon failure a three-part tuple where the first part is False, the second part is the
                        field value, and the third part is the error message.
        """

        if field not in cls.Meta.model.Meta.fields:
            return (False, field, "Unknown field name")

        return cls.Meta.model.Meta.fields[field].validate(value)

    # ------------------------------------------------------------------------------------------------------------------

    def values (self):
        """
        Retrieve all model values.

        @return (dict) The model key/value pairs.
        """

        return self.__dict__["_model_inst"].values()

# ----------------------------------------------------------------------------------------------------------------------

class DatabaseModelQuery:

    def __init__ (self, cls, filters, query_type="AND"):
        """
        Create a new DatabaseModelQuery instance.
        
        @param cls        (class) The parent DatabaseModel class under which this query will operate.
        @param filters    (tuple) The tuple or list consisting of tuples or lists of column, operator and value entries.
        @param query_type (str)   The type of filtering, either AND or OR.
        """

        if not isinstance(cls(), DatabaseModel):
            raise ModelException("%s is not a sub-class of DatabaseModel" % cls.__name__)

        if type(filters) not in (tuple, list):
            raise DatabaseModelException("Filters must be a tuple/list of tuples/lists")

        if query_type not in ("AND", "OR"):
            raise DatabaseModelException("Query type must be AND or OR")

        self._cls        = cls
        self._connection = None
        self._limit      = None
        self._offset     = None
        self._order      = None
        self._query      = "SELECT * FROM \"" + cls.Meta.table + "\" WHERE"
        self._query_type = " " + query_type
        self._values     = []

        for i, filter in enumerate(filters):
            if type(filter) not in (tuple, list) or len(filter) not in (3, 4):
                raise DatabaseModelException("Filter must be a tuple/list with 3 or 4 entries (field, operator, " \
                                             "value[, wrap])")

            if i > 0:
                self._query += self._query_type

            if len(filter) == 3:
                field    = filter[0]
                operator = filter[1]
                value    = filter[2]
                wrap     = None

            else:
                field    = filter[0]
                operator = filter[1]
                value    = filter[2]
                wrap     = filter[3]

            if value is None:
                if operator == "=":
                    self._query += " %s IS NULL" % field

                else:
                    self._query += " %s IS NOT NULL" % field

            elif type(value) in (tuple, list):
                ins = []

                for val in value:
                    ins.append("%s")
                    self._values.append(val)

                if operator == "=":
                    self._query += (" %s IN (" % field) + ",".join(ins) + ")"

                else:
                    self._query += (" %s NOT IN (" % field) + ",".join(ins) + ")"
            
            elif type(value) == bool:
                if value:
                    self._query += " %s" % field

                else:
                    self._query += " NOT %s" % field

            elif wrap:
                if type(value) == str and value.startswith("@"):
                    self._query += " %s(%s) %s %s(%s)" % (wrap, field, operator, wrap, value[1:])

                else:
                    self._query += " %s(%s) %s %s(%s)" % (wrap, field, operator, wrap, "%s")

                    self._values.append(value)

            elif type(value) == str and value.startswith("@"):
                self._query += " %s %s %s" % (field, operator, value[1:])

            else:
                self._query += " %s %s %s" % (field, operator, "%s")

                self._values.append(value)

    # ------------------------------------------------------------------------------------------------------------------

    def __call__ (self, convert=True):
        """
        Execute the query.

        @param convert (bool) Indicates that each record is to be converted into a model instance.

        @return (object) A list of records, upon success, otherwise None.
        """

        query = self._query
        meta  = self._cls.Meta

        if self._order:
            query += " ORDER BY %s" % self._order

        if self._offset:
            query += " OFFSET %d" % self._offset

        if self._limit:
            query += " LIMIT %d" % self._limit

        try:
            if self._connection:
                close      = False
                cursor     = None
                connection = self._connection

            else:
                close      = True
                cursor     = None
                connection = settings.databases[meta.database]["instance"].connection()

            cursor = connection.cursor()
            cursor.execute(query, self._values)

            records = []

            if convert:
                # convert all records to a model instance
                while True:
                    record = cursor.fetchone()

                    if not record:
                        break

                    records.append(self._cls(**dict(zip(meta.columns, record))))

            else:
                # don't convert records
                while True:
                    record = cursor.fetchone()

                    if not record:
                        break

                    records.append(dict(zip(meta.columns, record)))
            
            return records

        except Exception, e:
            raise DatabaseModelException(str(e))

        finally:
            if cursor:
                cursor.close()

            if close and connection:
                connection.close()

    # ------------------------------------------------------------------------------------------------------------------

    def __getitem__ (self, limit):
        """
        Set the limit of records.

        @param limit (int) The record limit.
        
        @return (object) This exact DatabaseModelQuery instance.
        """

        self.limit(limit)

        return self

    # ------------------------------------------------------------------------------------------------------------------

    def __getslice__ (self, offset, limit):
        """
        Set the offset and limit for this database query.

        @param offset (int) The record offset.
        @param limit  (int) The record limit.

        @return (object) This exact DatabaseModelQuery instance.
        """

        self.offset(offset)
        
        if limit > 1000000:
            # this is to protect from getslice functionality where if a limit isn't set, it is
            # assumed to be the value of the long max
            limit = None
            
        self.limit(limit)

        return self

    # ------------------------------------------------------------------------------------------------------------------

    def get_connection (self, connection):
        """
        Retrieve the current connection that is being used.
        
        @return (object) The live database connection, if set_connection() has assigned a connection, otherwise None.
        """

        return self._connection

    # ------------------------------------------------------------------------------------------------------------------

    def limit (self, limit):
        """
        Set the record limit.

        @param limit (int) The record limit.

        @return (object) This exact DatabaseModelQuery instance.
        """

        if type(limit) != int or limit < 0:
            raise DatabaseModelException("Invalid limit: %d" % limit)

        self._limit = limit

        return self

    # ------------------------------------------------------------------------------------------------------------------

    def offset (self, offset):
        """
        Set the record offset.
        
        @param offset (int) The record offset.

        @return (object) This exact DatabaseModelQuery instance.
        """

        if type(offset) != int or offset < 0:
            raise DatabaseModelException("Invalid offset: %d" % offset)

        self._offset = offset

        return self

    # ------------------------------------------------------------------------------------------------------------------

    def order (self, order):
        """
        Set the record order.

        @param order (str) The record order.

        @return (object) This exact DatabaseModelQuery instance.
        """

        if type(order) != str or len(order.strip()) == 0:
            raise DatabaseModelException("Invalid order: %s" % order)

        self._order = order

        return self

    # ------------------------------------------------------------------------------------------------------------------

    def set_connection (self, connection):
        """
        Set the connection that is used for this query interface.

        Note: Once a connection is passed it is the responsibility of the caller to close the connection.

        @param connection (object) The database connection.
        """

        self._connection = connection
