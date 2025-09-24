# Overview

We register IGSN IDs for heritage samples using DataCite’s 4.6 schema.
Our working schema is structured for Cordra, but each field has a clear mapping
to DataCite for DOI registration.

**Key points:**
- Identifier is always a DOI, even if Cordra has its own internal ID.
- Resource type must use `PhysicalObject` for IGSN samples.
- Relations (subsamples, heritage objects) must use DataCite `relationType` values.
- Metadata is exported as valid DataCite JSON for deposit.

References:
- [DataCite Schema 4.6](https://datacite-metadata-schema.readthedocs.io/en/4.6/)
- [IGSN metadata recommendations](https://support.datacite.org/docs/igsn-id-metadata-recommendations)
