#! /usr/bin/env python
#
# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Noah Fontes <nfontes@invectorate.com>

from setuptools import setup, find_packages

setup(
    name = "Elements",
    description = "A collection of useful libraries for Python",
    long_description = open("README").read(),

    version = "0.1.1a1",

    author = "Sean Kerr",
    author_email = "sean@code-box.org",

    packages = find_packages("lib"),
    package_dir = {"": "lib"},

    license = "BSD",
    url = "http://github.com/feti/Elements"
)
