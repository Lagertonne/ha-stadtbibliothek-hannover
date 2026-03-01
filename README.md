# HA Stadtbibliothek Hannover Integration

This integration adds information from the Stadtbibliothek Hannover into homeassistant

## Usage

You can add the integration by using HACS. Just add the repository as a custom repository. I'm currently not doing any versioning, so you have to update the repository manually.

After installing, you have to configure the integration via the `configuration.yaml`. Example entry:

```
sensor:
  - platform: stb_hannover
    username: USERNAME
    password: PASSWORD
```

Just replace USERNAME and PASSWORD with the username and pasword you are using when accessing the web portal.

After configuration, you should have to new sensors: 
  * `sensor.next_return_date`
    * This sensor returns the earliest date, when a book has to be returned
  * `sensor.loaned_books_USERNAME`
    * This sensor returns the number of currently loaned books. In the attributes, you can find a more detailed list of all books

## Known/Potential issues
  * No experience what happens when no book is currently loaned
  * Multi-User is not tested
  * No releases/versioning
  * Refresh has not been tested
  * The integration refreshes the state every hour, keep this in mind when returning books and not seeing an immediate change

