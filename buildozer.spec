[app]
title = SNC Shetkari Bazar
package.name = sncshetkaribazar
package.domain = com.snc
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,txt
version = 1.0.0
requirements = python3,kivy,pillow,plyer,pyjnius,charset_normalizer==2.1.1,idna,urllib3,certifi
orientation = portrait
fullscreen = 0

# Android
android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.permissions = INTERNET
android.accept_sdk_license = True

# Build settings
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1

