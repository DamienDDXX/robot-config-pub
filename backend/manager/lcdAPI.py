#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import smbus
import logging
import traceback


# 常量定义
LCD_CMD_BACKLIT_OFF = 0x10
LCD_CMD_BACKLIT_ON  = 0x11

LCD_CMD_PAGE_LOGO   = 0x12
LCD_CMD_PAGE_WAIT   = 0x13
LCD_CMD_PAGE_BLINK  = 0x14
LCD_CMD_PAGE_FAIL   = 0x15
LCD_CMD_PAGE_HAPPY  = 0x16
LCD_CMD_PAGE_LISTEN = 0x17
LCD_CMD_PAGE_SAD    = 0x18
LCD_CMD_PAGE_SMILE  = 0x19

lcd_busy = False

# 液晶接口类
class lcdAPI(object):
    # 初始化
    def __init__(self):
        self._backlit = True
        self._bus = smbus.SMBus(1)

    def command(self, cmd):
        global lcd_busy
        try:
            for wait in range(0, 10):
                if not lcd_busy:
                    break
                time.sleep(0.1)
            lcd_busy = True
            self._bus.write_byte(cmd, 0x00)
            time.sleep(0.1)
            lcd_busy = False
        except IOError:
            pass

    # 切换背光开关
    def backlit_switch(self):
        if self._backlit:
            self.backlit_off()
        else:
            self.backlit_on()

    def notify_alive(self):
        if self._backlit:
            self.backlit_on()
        else:
            self.backlit_off()

    def backlit_off(self):
        self._backlit = False
        self.command(LCD_CMD_BACKLIT_OFF)

    def backlit_on(self):
        self._backlit = True
        self.command(LCD_CMD_BACKLIT_ON)

    def page_logo(self):
        self.command(LCD_CMD_PAGE_LOGO)

    def page_wait(self):
        self.command(LCD_CMD_PAGE_WAIT)

    def page_blink(self):
        self.command(LCD_CMD_PAGE_BLINK)

    def page_fail(self):
        self.command(LCD_CMD_PAGE_FAIL)

    def page_happy(self):
        self.command(LCD_CMD_PAGE_HAPPY)

    def page_listen(self):
        self.command(LCD_CMD_PAGE_LISTEN)

    def page_sad(self):
        self.command(LCD_CMD_PAGE_SAD)

    def page_smile(self):
        self.command(LCD_CMD_PAGE_SAD)


################################################################################
# 测试程序
if __name__ == '__main__':
    lcd = lcdAPI()
    try:
        while True:
            time.sleep(1)
            lcd.backlit_off()
            time.sleep(1)
            lcd.backlit_on()
            time.sleep(1)
            lcd.page_logo()
            time.sleep(1)
            lcd.page_wait()
            time.sleep(1)
            lcd.page_blink()
            time.sleep(1)
            lcd.page_fail()
            time.sleep(1)
            lcd.page_happy()
            time.sleep(1)
            lcd.page_listen()
            time.sleep(1)
            lcd.page_sad()
            time.sleep(1)
            lcd.page_smile()
    except KeyboardInterrupt:
        time.sleep(1)
        lcd_backlit_on()

