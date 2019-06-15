/** DB for tracking distribution ecm effort */

/* TODO: delete before 1.0.0 */
DROP TABLE IF EXISTS ecm_curve;
DROP TABLE IF EXISTS numbers;
DROP TABLE IF EXISTS factors;

CREATE TABLE IF NOT EXISTS ecm_curve (
  num_id INTEGER NOT NULL,
  curve_id INTEGER NOT NULL,

  B1 INTEGER NOT NULL,
  B2 INTEGER NOT NULL,

  stage1_chkpnt TEXT,

  maxmem INTEGER NOT NULL,
  stage1_ms INTEGER NOT NULL,
  stage2_ms INTEGER NOT NULL,

  /* ecm = 1, pm1 = 2, pp1 = 3 */
  method INTEGER NOT NULL CHECK(method >= 1 AND method <= 3),

  timestamp INTEGER NOT NULL,

  /* TODO: x, y, param, sigma */
  /* TODO: A, torsion, k, power, dickson */
  /* TODO: ecm-version */

  FOREIGN KEY (num_id) REFERENCES numbers(num_id),
  PRIMARY KEY (num_id, curve_id)
);

CREATE TABLE IF NOT EXISTS numbers (
  num_id INTEGER PRIMARY KEY AUTOINCREMENT,
  n      TEXT NOT NULL,
  n_expr TEXT NOT NULL,
  /**
   * P = 1, PRP = 2, FF = 3,
   * CF = 4, C = 5
   */
  status INTEGER NOT NULL CHECK(status >= 1 AND status <= 5)
);

CREATE TABLE IF NOT EXISTS factor (
  num_id_c INTEGER NOT NULL,
  num_id_f INTEGER NOT NULL,

  FOREIGN KEY(num_id_c) REFERENCES numbers(num_id),
  FOREIGN KEY(num_id_f) REFERENCES numbers(num_id),
  PRIMARY KEY(num_id_c, num_id_f)
);

