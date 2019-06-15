
/** Main table distribution ecm effort */

CREATE TABLE IF NOT EXISTS ecm_curve (
  PRIMARY_KEY(num_id, curve_id),

  num_id INTEGER NOT NULL REFERENCES(numbers),
  curve_id INTEGER NOT NULL,

  B1 INTEGER NOT NULL,
  B2 INTEGER NOT NULL,

  stage1_chkpnt text,

  maxmem INTEGER NOT NULL,
  stage1_ms INTEGER NOT NULL,
  stage2_ms INTEGER NOT NULL,

  /* ecm = 1, pm1 = 2, pp1 = 3 */
  method INTEGER NOT NULL CHECK(method >= 1 and method <= 3),

  timestamp INTEGER NOT NULL


  /* TODO: x, y, param, sigma */
  /* TODO: A, torsion, k, power, dickson */
  /* TODO: ecm-version */
)

CREATE TABLE IF NOT EXISTS numbers (
  num_id INTEGER NOT NULL PRIMARY KEY
  n text NOT NULL,
  n_expr NOT NULL,

  /**
   * P = 1, PRP = 2, FF = 3,
   * CF = 4, C = 5
   */
  status INTEGER NOT NULL CHECK(status >= 1 and status <= 5),
)

CREATE TABLE IF NOT EXISTS factor (
  PRIMARY KEY(num_id_c, num_id_f),

  num_id_c INTEGER NOT NULL REFERENCES(numbers),
  num_id_f INTEGER NOT NULL REFERENCES(numbers)

)

