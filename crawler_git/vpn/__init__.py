"""
VPN应用打开功能模块
"""
from .open_privadovpn import (
    open_privadovpn, 
    check_privadovpn_running, 
    open_privadovpn_if_not_running,
    click_connect_button,
    open_and_connect_privadovpn,
    close_privadovpn
)

__all__ = [
    'open_privadovpn', 
    'check_privadovpn_running', 
    'open_privadovpn_if_not_running',
    'click_connect_button',
    'open_and_connect_privadovpn',
    'close_privadovpn'
]

