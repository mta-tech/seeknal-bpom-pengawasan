# Varian C — GATED PROCEDURE (pengetahuan = Varian A persis)

**Hipotesis (H3):** masalahnya DISIPLIN PROSES, bukan isi pengetahuan — turn gagal ditandai
eksplorasi liar 20-36 SQL tanpa rencana. Gerbang berurutan + anggaran keras (max 6 SQL/turn,
stop rules eksplisit) memperbaiki akurasi & biaya, dengan pengetahuan yang sama.

**Desain:** context/ = SALINAN PERSIS varian A (isolasi murni efek prosedur: C vs A hanya beda
orkestrasi). SEEKNAL_ASK = 5 gerbang (CLASSIFY→CLARIFY→RESOLVE→COMMIT→EXECUTE→VERIFY) dengan
anggaran & stop rules. Skill analyst menegakkan budget ledger.

**Harness:** sama dengan A/B. Lihat `docs/planning/2026-07-15-three-hypothesis-experiment.md`.
