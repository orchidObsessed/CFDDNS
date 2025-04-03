# Tiny Cloudflare Dynamic DNS

This is a lightweight script designed to provide dynamic DNS functionality to any zone. This script has no dependencies; just run it on any version of Python 3.

To get started, set this up to run on an interval, perhaps with `cron` or `taskschd.msc`, provide account information, and you're set!

## Environment Variables

You must provide certain environment variables. These may either be passed in as a `.env` file (which should be placed at the same directory as the Python file), or as environment variables via your OS. Either way, you must provide the following:

| Key Name | Description |
| -------- | ----------- |
| `api_key` | The API key that has zone record read/write privileges. |
| `zone_name` | The name of the zone (eg. example.com) |
| `zone_id` | The ID of the zone. |

There are two things to note. First, the `.env` file takes precedence over environment variables. Second, if you do use a `.env` file, it should be of the form:

```
api_key=abc123
zone_name=example.com
zone_id=def456
```

Note that there are **no** spaces between the equals sign and the key/value. The order of keys and values does not matter.