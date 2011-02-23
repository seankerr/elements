# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

APP_AUTHOR  = "Sean Kerr"
APP_EMAIL   = "sean@code-box.org"
APP_GIT     = "http://github.com/feti/Elements.git"
APP_NAME    = "Elements"
APP_VERSION = "0.1.1-alpha"

# ----------------------------------------------------------------------------------------------------------------------

def include (mod_path):
    """
    Include a module or a particular attribute of a module.

    @param mod_path (str) The library path to the item that will be dynamically imported.
    """

    # assume that mod_path is an attribute
    try:
        mod_fullpath, mod_attr = mod_path.rsplit(".", 1)

        mod = __import__(mod_fullpath, globals(), locals(), [mod_attr], -1)

        return getattr(mod, mod_attr)

    except AttributeError:
        pass

    except Exception, e:
        raise Exception("Failed to include module or attribute '%s': %s" % (mod_path, str(e)))

    # perhaps mod_path is a module
    try:
        return __import__(mod_path, globals(), locals(), [], -1)

    except:
        raise Exception("Failed to include module or attribute '%s'" % mod_path)
