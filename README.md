# Livebox Call Monitor (Home Assistant integration)

Log **every call** (incoming / outgoing / missed) from your **Orange Livebox**
directly in Home Assistant — with **contact names**, **tags**, **live ring
events**, and a **bundled Lovelace card** that does full contacts CRUD, all
native. No containers, no external apps.

[![hacs][hacs-badge]][hacs]

## Features

- 🔌 **UI setup** (config flow) — just enter your Livebox URL + admin password
- 📞 **Call log** — `last_call`, `call_log` (full history in attributes),
  `calls_today`, `missed_calls` sensors
- 👤 **Contacts** — stored in HA; caller **names + tags** shown everywhere
- 🎴 **Bundled card** — call log + contacts add/edit/delete, plus **“＋ name”**
  on any unknown caller — manage everything from one HA card
- 🔴 **Live ring events** — fires a `livebox_callmon_ring` event the moment the
  phone rings, and `livebox_callmon_new_call` when a call is logged
- 🏷️ **Tags** — family / work / spam / other (spam flagged red on the card)
- 🌍 **Number normalisation** — `+33…` and `0…` map to one contact

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/aghediri/ha-livebox-callmon` → category **Integration**.
2. Install **Livebox Call Monitor**, restart HA.
3. **Settings → Devices & Services → Add Integration → Livebox Call Monitor**.
   Enter your Livebox URL (`http://192.168.1.1`), username (`admin`), and admin
   password.

## The card

Add the resource (HACS usually auto-adds it; otherwise Settings → Dashboards →
Resources → `+` → URL `/livebox_callmon/card.js`, type **JavaScript Module**).

Then add a card:

```yaml
type: custom:livebox-callmon-card
entity: sensor.landline_call_log      # your call_log sensor
```

You get a two-tab card: **Call Log** (with ＋name on unknown callers) and
**Contacts** (add/edit/delete). Everything writes back through the integration.

## Services

| Service | Fields |
|---|---|
| `livebox_callmon.add_contact` | `number`, `name`, `tag?`, `notes?` |
| `livebox_callmon.edit_contact` | `number`, `name?`, `tag?`, `notes?`, `new_number?` |
| `livebox_callmon.delete_contact` | `number` |

## Events (for automations)

- `livebox_callmon_ring` — fires when the phone starts ringing
  (`event_data.last_call` has the most recent caller).
- `livebox_callmon_new_call` — fires when a new call is logged (event data is
  the enriched call: `number`, `name`, `direction`, `tag`, `duration`, …).

Example — announce ringing on a speaker / push via ntfy:

```yaml
alias: Landline ringing
trigger:
  - platform: event
    event_type: livebox_callmon_ring
action:
  - service: notify.mobile_app_xxx
    data:
      title: "Landline ringing"
      message: >
        {{ trigger.event_data.last_call.name
           or trigger.event_data.last_call.number }}
```

## How it works

The integration talks to the Livebox `sysbus` API
(`sah.Device.Information:createContext` for auth, then
`VoiceService.VoiceApplication:getCallList`), polling on your chosen interval
and watching voice state for live ring detection. Verified against Livebox 5;
should work on Livebox 4/6 with the same API.

## Notes

- Orange does not expose your SIP credentials, so this **logs** calls — it does
  not place/answer them.
- Contacts persist in HA storage (`.storage/livebox_callmon_contacts`).

## License

MIT

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
