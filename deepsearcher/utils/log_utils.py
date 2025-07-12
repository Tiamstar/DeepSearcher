#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log utilities - 兼容性模块
从 log.py 导入 get_logger 函数以保持向后兼容
"""

from .log import get_logger

__all__ = ['get_logger'] 