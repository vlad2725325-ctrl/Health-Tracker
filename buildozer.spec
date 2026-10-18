[app]
title = Health Tracker
package.name = healthtracker
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 0.1
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = ACTIVITY_RECOGNITION,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION
android.accept_sdk_license = True
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
