# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance
