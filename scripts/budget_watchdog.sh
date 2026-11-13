#!/usr/bin/env bash
# Backstop for the $25 AWS cap: stop the instance at 2026-11-13 20:00 UTC (~29.5 h of uptime) unless ~/keep_alive exists.
until [ "$(date -u +%s)" -ge "$(date -u -d '2026-11-13 20:00' +%s)" ]; do sleep 60; done
[ -f ~/keep_alive ] || sudo shutdown -h now
