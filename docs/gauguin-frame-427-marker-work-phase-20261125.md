# 0419 marker work allowance comparison

The passive 7.2 ms run found native submission beginning 6.6–9.1 ms
after the requested flip cutoff in two exact cases. Three other exact
cases reached hardware completion in time and staged close to the
deadline. Keep the 0425 kernel, signed marker, ready worker, GPU clock,
row copies and flip guard. Move the existing compositor notice 5 ms
earlier by setting its work allowance to 12.2 ms.

The fit and dispatch replay retains all 2,691 eligible sends using
the hardware edge trace and the largest recorded dispatch delay plus
one millisecond. The extra work allowance can absorb ordinary staging
tails. Its effect on missed producer turns needs the physical A/B.
Use paired controller CRCs for all 30 fixed seconds and sliding windows.
Compare the exact native deadline cases with the 7.2 ms control after
independent restoration.
