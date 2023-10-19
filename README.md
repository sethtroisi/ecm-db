# Design

[2023/10/19] Writing down some thoughts about what my dream ECM setup would be.


## Goals

1. Record what work (e.g. curves/B1/B2) has been done
1. Estimate t-level completion
1. Keep queue of work

## Rough Design

Based on pull based client model from CADO-nfs, primenet, BOINC.

### Sequence Diagram

```mermaid
sequenceDiagram;
    participant F as Front End
    participant S as Server
    participant GC as GPU_Client
    participant CC as CPU_Client

    F->>+S: Queue Curves(N, B1, B2)

    GC->>+S: get_stage_1_work
    activate GC
    S-->>-GC: reserve_stage_1
    GC->>S: upload_stage1_results
    deactivate GC
    S-->>F: progress

    CC->>S: reserve_stage2_work
    activate CC
    S-->>CC: reservation
    CC->>S: upload_stage2_results
    deactivate CC

    S-->>-F: progress
```

### Server

Python that tracks state

* Number
* Curves (B1, B2, count) complete
* Any factors that have been found.
* Stage 1 results and reservations
* For pratical purposes this probably needs to record finished curves (sigma) ranges

API:

* `get_stage1_work`
* `upload_stage1_results`
* `reserve_stage2_work`
* `upload_stage2_results`

### Client

Python wrapper around gmp-ecm ("ecm") that supports two modes (stage 1, stage2)

Runs "ecm" and tracking saving (and uploading) output

### Front-end

Some front-end to the server that lets you see factors found, query progress, queue numbers

## Complications

Trying to learn from [WraithX's ecm.py](https://www.mersenneforum.org/showthread.php?t=15508).

Features to name a few

* Canceling other stage2 curves when factor found

Difficulties

* Lots of code to communicate with ecm
  * Lots of code related to setting arguments
    * maxmem: Learning from prime95 it's a hard problem to choose optimal memory split between workers.


## Open Questions

### 1 client for many ecm instances?

Pros:
  * Max mem is easier (split equally)
  * Easy to stop early
  * Can reserve all of a number's stage 1 curves without worrying about things to much
Cons:
  * Makes code uglier for multiple work units at the same time...

### Would this make more sense inside BOINC / PrimeNet?

Does BOINC support not verifying workunits?
Is there some way to verify ECM results?
  * Seems vaguely like VDF could be adopted
  * Any VDF papers covering elliptic curves?
