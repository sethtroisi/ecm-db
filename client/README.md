# ECM-Runner
Tool to run and report a ecm-db workunit

---

### MVP

- [ ] arg list
- [ ] output
- [ ] report result to server

### Testing

```shell
# Finds 26 digit factor quickly
python ecm_runner.py -b ../../gmp-ecm/ecm -n "(2^293-1)" --B1 4e5 -t 6 -- -power 3

# Finds 32 digit factor slowly
python ecm_runner.py -b ../../gmp-ecm/ecm -n "(2^349-1)/1779973928671" --B1 1e6 -t 6

# Test resuming a file
python ecm_runner.py -b ../../gmp-ecm/ecm --resume resume.16 --B1 10000000000 --B2 2e14 -t 4
```

### Long term goals

- [ ] tests
- [ ] local checkpointing
- [ ] RAM coordination
  - I wrote something about this somewhere go find it
