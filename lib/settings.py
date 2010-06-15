# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author:  Sean Kerr <sean@code-box.org>
# Version: $Id$

# ----------------------------------------------------------------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------------------------------------------------------------

# import psycopg2
#
#databases = {
#    "default": {
#        "host":   "localhost",
#        "user":   "user",
#        "passwd": "password",
#        "db":     "dbname",
#        "pool":   5,
#        "api":    psycopg2
#    }
#}

# ----------------------------------------------------------------------------------------------------------------------
# MODEL
# ----------------------------------------------------------------------------------------------------------------------

model_required_err       = "This is required"
model_boolean_type_err   = "Invalid boolean value"
model_date_type_err      = "Invalid date"
model_datetime_type_err  = "Invalid date/time"
model_domain_type_err    = "Invalid domain"
model_email_type_err     = "Invalid email address"
model_float_max_err      = "Maximum size is $3"
model_float_min_err      = "Minimum size is $3"
model_float_type_err     = "Invalid decimal value"
model_int_max_err        = "Maximum size is $3"
model_int_min_err        = "Minimum size is $3"
model_int_type_err       = "Invalid numerical value"
model_ipaddress_type_err = "Invalid IP Address"
model_money_max_err      = "Maximum size is $3"
model_money_min_err      = "Minimum size is $3"
model_money_type_err     = "Invalid money value"
model_text_max_err       = "Maximum length is $3 characters"
model_text_min_err       = "Minimum length is $3 characters"
model_text_regex_err     = "Invalid format"
model_text_type_err      = "Invalid value"
model_time_type_err      = "Invalid time"
model_url_type_err       = "Invalid URL"