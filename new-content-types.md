# adding new content-type versions to lax

- [ ] start a new branch
- [ ] ensure the api-raml has these new specs present
- [ ] open src/core/settings.py for editing
- [ ] change REST_FRAMEWORK, add new content type version
- [ ] change ALL_SCHEMA_IDX, add new content type version
- [ ] in `src/publisher/negotiation.py`, change `_dynamic_types` and add new content type version
- [ ] in `src/publisher/middleware.py`, add any content-type downgrades

