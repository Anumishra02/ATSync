==============================================================================
Step 3: agreement -- covered / not-covered / blended (never blended alone)
==============================================================================

--- COVERED (n=10) -- the baseline. Protect this number. ---
n=10  rho=+0.543  p=0.1050  raw_MAE=18.40  scale-corrected_MAE=15.20  95% CI=[-0.229, +0.961]
Covered rho is low -> this is a genuine scoring bug on the one domain the matcher can see, not a taxonomy-coverage artifact. Step 4's within-covered disagreement ranking should name the dimension to fix.

--- NOT COVERED (n=28) (R31 dropped: duplicate of R30, see module docstring) -- taxonomy-gap evidence, not scoring failure ---
n=28  rho=-0.182  p=0.3551  raw_MAE=20.89  scale-corrected_MAE=16.14
rho(lost_share, human_total) within not-covered: rho=+0.105 p=0.5959 (n=28) -- tests whether the inversion above is a real mechanism (stronger resumes losing more taxonomy credit) or noise from tiny integer skill-count denominators. |rho| this small says noise, not mechanism.

--- BLENDED (n=38) (R31 dropped: duplicate of R30, see module docstring) -- quantifies the drag only, never the headline ---
n=38  rho=+0.115  p=0.4917  raw_MAE=20.24  scale-corrected_MAE=15.89
Blended rho (+0.115) is dragged down by the 28 not-covered resumes. Do NOT tune the scorer to move this number -- grow the taxonomy instead.

==============================================================================
MAE arithmetic check -- experience is a scale mismatch, not missing data
==============================================================================
  covered      raw= 18.40  scale-corrected= 15.20  (scale mismatch explains +3.20 of the raw MAE, 17.4% of it)
  not_covered  raw= 20.89  scale-corrected= 16.14  (scale mismatch explains +4.75 of the raw MAE, 22.7% of it)
  blended      raw= 20.24  scale-corrected= 15.89  (scale mismatch explains +4.34 of the raw MAE, 21.5% of it)
The correction is real but partial: it accounts for a few points of the raw MAE in every block, not most of it. A substantial calibration gap remains on the scale-matched comparison -- report scale-corrected MAE as the real number, not the raw one, but don't treat the correction as having explained the gap away.

==============================================================================
Coverage -- how often ATSync can produce a complete score at all
==============================================================================
  covered      9/10 complete scores
  not_covered  18/28 complete scores
  blended      27/38 complete scores

==============================================================================
Per-dimension signed gaps (machine - human, 0-100 scale), COVERED set only
==============================================================================
  relevance      mean signed gap= -37.46  mean |gap|= 38.63  (n=10/10)
  skills         mean signed gap= -36.13  mean |gap|= 36.13  (n=10/10)
  experience     UNCOMPUTABLE -- ATSync has no scorer for experience depth/ordering/completeness. Human rubric weights it 20/100 (joint-highest with achievements).
  achievements   mean signed gap= -31.33  mean |gap|= 31.33  (n=9/10)  (1 row(s) uncomputable, dropped)
  writing        mean signed gap= -33.50  mean |gap|= 39.17  (n=10/10)
  structure      mean signed gap=  +6.33  mean |gap|= 10.66  (n=10/10)

==============================================================================
Headline
==============================================================================
Covered n=10: rho = 0.543 (p = 0.105, 95% CI -0.229 to +0.961), scale-corrected MAE = 15.20 (raw was 18.40); not-covered n=28: rho = -0.182; rho(lost_share, human_total) within not-covered = +0.105 (p=0.596, noise not mechanism); experience dimension structurally absent (20/100 pts, excluded from both sides, not a gap to close); coverage: 9/10 complete scores in covered, 27/38 overall; largest signed per-dimension gap is -37.46 on relevance (n=10/10).
