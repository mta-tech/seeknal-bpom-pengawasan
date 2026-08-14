# Profil Kolom Live — database `pengawasan` (2026-08-13)

Per kolom: jumlah NULL (SQL NULL, bukan sentinel string), persentase, dan cacah nilai distinct.
Diikuti katalog nilai untuk kolom berkardinalitas rendah.

---


### coverage_balai  —  668 rows
  - id_balai                             bigint       null=        0 (  0.0%)  distinct=88
  - nama_balai                           text         null=        0 (  0.0%)  distinct=88
  - id_kabupaten                         integer      null=        0 (  0.0%)  distinct=514
  - kabupaten_kota                       text         null=        0 (  0.0%)  distinct=514
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1

### mv_pengawasan  —  183,968 rows
  - id                                   bigint       null=        0 (  0.0%)  distinct=172180
  - nomor_surat                          text         null=        0 (  0.0%)  distinct=9742
  - komoditi                             text         null=        0 (  0.0%)  distinct=7
  - nama_balai                           text         null=        0 (  0.0%)  distinct=84
  - tgl_start                            date         null=        0 (  0.0%)  distinct=1313
  - tgl_end                              date         null=        0 (  0.0%)  distinct=1314
  - nama_produk                          text         null=        0 (  0.0%)  distinct=42856
  - nie                                  text         null=        0 (  0.0%)  distinct=41213
  - pendaftar                            text         null=        0 (  0.0%)  distinct=6584
  - media_iklan                          text         null=        0 (  0.0%)  distinct=5
  - lokasi_iklan                         text         null=        0 (  0.0%)  distinct=118058
  - jenis_pembuat_iklan                  text         null=        0 (  0.0%)  distinct=3
  - kesimpulan_penilaian_akhir           text         null=        0 (  0.0%)  distinct=3
  - kesimpulan_penilaian_balai           text         null=        0 (  0.0%)  distinct=5
  - kesimpulan_penilaian_pusat           text         null=        0 (  0.0%)  distinct=6
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[komoditi] (7): KOSMETIKA=48,325 | ROKOK=40,031 | PRODUK PANGAN=33,777 | OBAT=32,180 | OBAT TRADISIONAL (OT)=19,003 | SUPLEMEN KESEHATAN=7,821 | OBAT KUASI=2,831
    VALUES[media_iklan] (5): ELEKTRONIK=98,079 | MEDIA_LUARRUANG=56,064 | CETAK=25,028 | MEDIA_LAIN=3,825 | =972
    VALUES[jenis_pembuat_iklan] (3): =150,191 | PELAKU USAHA=29,290 | PERORANGAN=4,487
    VALUES[kesimpulan_penilaian_akhir] (3): MK=67,920 | Null=64,391 | TMK=51,657
    VALUES[kesimpulan_penilaian_balai] (5): MK=111,175 | TMK=62,702 | TMK MAYOR=3,828 | TMK MINOR=3,431 | Null=2,832
    VALUES[kesimpulan_penilaian_pusat] (6): MK=63,723 | Null=55,889 | TMK=50,934 | TMK KRITIKAL=8,684 | TMK MINOR=2,420 | TMK MAYOR=2,318

### mv_pengawasan_agg  —  118,133 rows
  - periode_type                         text         null=        0 (  0.0%)  distinct=2
  - tanggal_periode                      date         null=        0 (  0.0%)  distinct=1314
  - komoditi                             text         null=        0 (  0.0%)  distinct=7
  - nama_balai                           text         null=        0 (  0.0%)  distinct=84
  - media_iklan                          text         null=        0 (  0.0%)  distinct=5
  - jenis_pembuat_iklan                  text         null=        0 (  0.0%)  distinct=3
  - kesimpulan_penilaian_akhir           text         null=        0 (  0.0%)  distinct=3
  - kesimpulan_penilaian_balai           text         null=        0 (  0.0%)  distinct=5
  - kesimpulan_penilaian_pusat           text         null=        0 (  0.0%)  distinct=6
  - jumlah_pengawasan                    bigint       null=        0 (  0.0%)  distinct=77
  - jumlah_surat_unik                    bigint       null=        0 (  0.0%)  distinct=32
  - jumlah_produk_unik                   bigint       null=        0 (  0.0%)  distinct=63
  - jumlah_nie_unik                      bigint       null=        0 (  0.0%)  distinct=63
  - jumlah_pendaftar_unik                bigint       null=        0 (  0.0%)  distinct=39
  - avg_durasi_hari                      double precision null=        0 (  0.0%)  distinct=938
  - min_durasi_hari                      integer      null=        0 (  0.0%)  distinct=66
  - max_durasi_hari                      integer      null=        0 (  0.0%)  distinct=74
  - last_updated                         timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[periode_type] (2): day=70,746 | month=47,387
    VALUES[komoditi] (7): PRODUK PANGAN=27,128 | KOSMETIKA=26,423 | OBAT=18,834 | OBAT TRADISIONAL (OT)=17,915 | ROKOK=14,005 | SUPLEMEN KESEHATAN=9,732 | OBAT KUASI=4,096
    VALUES[media_iklan] (5): ELEKTRONIK=66,491 | MEDIA_LUARRUANG=27,746 | CETAK=19,604 | MEDIA_LAIN=3,336 | =956
    VALUES[jenis_pembuat_iklan] (3): =91,005 | PELAKU USAHA=22,395 | PERORANGAN=4,733
    VALUES[kesimpulan_penilaian_akhir] (3): Null=59,427 | MK=36,771 | TMK=21,935
    VALUES[kesimpulan_penilaian_balai] (5): MK=70,900 | TMK=34,391 | TMK MAYOR=4,429 | TMK MINOR=4,315 | Null=4,098
    VALUES[kesimpulan_penilaian_pusat] (6): MK=45,060 | Null=36,416 | TMK=21,382 | TMK KRITIKAL=8,741 | TMK MINOR=3,478 | TMK MAYOR=3,056
    VALUES[jumlah_pengawasan] (77): 1=57,257 | 2=21,542 | 3=11,402 | 4=7,111 | 5=4,879 | 6=3,349 | 7=2,456 | 8=1,869 | 9=1,348 | 10=1,222 | 11=767 | 12=704 | 13=593 | 14=443 | 15=440 | 16=329 | 17=313 | 18=251 | 19=214 | 20=198 | 21=178 | 22=151 | 23=127 | 24=110 | 25=76 | 26=68 | 27=65 | 31=63 | 29=59 | 28=58 | 32=46 | 35=45 | 34=44 | 30=42 | 33=35 | 39=23 | 36=22 | 38=21 | 37=21 | 44=20 | 40=15 | 41=15 | 42=14 | 43=13 | 45=12 | 50=10 | 48=9 | 49=9 | 53=8 | 47=7 | 58=7 | 52=6 | 56=4 | 54=3 | 55=3 | 57=3 | 51=3 | 69=3 | 46=3 | 64=2 | 61=2 | 63=2 | 66=2 | 68=2 | 82=2 | 102=2 | 67=1 | 89=1 | 96=1 | 111=1 | 72=1 | 60=1 | 75=1 | 62=1 | 104=1 | 117=1 | 170=1
    VALUES[jumlah_surat_unik] (32): 1=106,869 | 2=8,681 | 3=1,574 | 4=471 | 5=193 | 6=104 | 7=61 | 8=46 | 9=23 | 10=23 | 13=8 | 11=8 | 12=7 | 17=6 | 20=6 | 34=6 | 15=6 | 16=5 | 26=4 | 29=4 | 31=4 | 18=4 | 14=4 | 24=4 | 22=3 | 33=2 | 19=2 | 28=1 | 21=1 | 32=1 | 23=1 | 27=1
    VALUES[jumlah_produk_unik] (63): 1=58,416 | 2=21,746 | 3=11,439 | 4=7,182 | 5=4,800 | 6=3,260 | 7=2,455 | 8=1,774 | 9=1,315 | 10=1,049 | 11=702 | 12=676 | 13=541 | 14=458 | 15=376 | 16=315 | 17=271 | 18=233 | 19=184 | 20=138 | 21=128 | 22=107 | 23=95 | 24=71 | 25=61 | 27=46 | 26=45 | 28=39 | 30=33 | 29=30 | 31=20 | 33=17 | 32=16 | 35=12 | 34=12 | 36=10 | 43=5 | 38=5 | 39=5 | 40=5 | 37=4 | 53=3 | 46=3 | 45=3 | 41=2 | 58=2 | 42=2 | 47=2 | 48=2 | 49=2 | 50=2 | 55=2 | 57=2 | 97=1 | 44=1 | 52=1 | 56=1 | 67=1 | 69=1 | 159=1 | 104=1 | 80=1 | 100=1
    VALUES[jumlah_nie_unik] (63): 1=68,312 | 2=19,187 | 3=9,811 | 4=5,952 | 5=3,971 | 6=2,604 | 7=1,809 | 8=1,342 | 9=981 | 10=851 | 11=564 | 12=499 | 13=371 | 14=316 | 15=305 | 16=215 | 17=181 | 18=143 | 19=128 | 20=98 | 21=80 | 22=77 | 23=44 | 24=44 | 25=38 | 26=32 | 28=23 | 27=19 | 30=17 | 31=16 | 29=15 | 34=12 | 32=9 | 33=7 | 36=7 | 35=5 | 37=5 | 43=5 | 38=4 | 39=4 | 45=3 | 41=2 | 49=2 | 47=2 | 44=2 | 42=2 | 57=1 | 166=1 | 60=1 | 61=1 | 62=1 | 68=1 | 110=1 | 104=1 | 80=1 | 53=1 | 102=1 | 46=1 | 50=1 | 52=1 | 40=1 | 54=1 | 55=1
    VALUES[jumlah_pendaftar_unik] (39): 1=74,119 | 2=19,832 | 3=9,278 | 4=5,038 | 5=3,104 | 6=2,026 | 7=1,293 | 8=908 | 9=636 | 10=466 | 11=337 | 12=275 | 13=198 | 15=144 | 14=139 | 16=86 | 18=45 | 17=40 | 20=33 | 19=24 | 23=19 | 22=18 | 21=14 | 24=11 | 26=8 | 25=7 | 27=6 | 30=6 | 28=5 | 29=4 | 33=3 | 45=3 | 35=2 | 58=1 | 46=1 | 31=1 | 32=1 | 34=1 | 65=1
    VALUES[min_durasi_hari] (66): 0=98,308 | 30=5,164 | 29=4,204 | 1=2,056 | 28=1,255 | 27=1,049 | 25=534 | 24=415 | 26=393 | 23=381 | 22=345 | 2=274 | 4=271 | 20=261 | 3=252 | 9=252 | 21=230 | 19=224 | 14=213 | 31=209 | 7=202 | 6=167 | 15=156 | 8=156 | 16=132 | 18=127 | 17=118 | 5=105 | 11=94 | 12=84 | 40=80 | 13=75 | 39=60 | 10=57 | 35=31 | 32=24 | 33=22 | 60=18 | 38=18 | 34=16 | 36=12 | 59=10 | 41=9 | 61=7 | 47=6 | 111=6 | 42=5 | 364=5 | 77=5 | 153=4 | 65=4 | 56=4 | 58=4 | 37=3 | 66=2 | 109=2 | 139=2 | 226=2 | 88=2 | 335=1 | 45=1 | 46=1 | 48=1 | 150=1 | 50=1 | 55=1
    VALUES[max_durasi_hari] (74): 0=95,235 | 30=5,859 | 29=4,640 | 1=2,644 | 28=1,440 | 27=1,153 | 25=582 | 24=450 | 26=436 | 23=422 | 22=391 | 4=353 | 2=335 | 3=316 | 20=283 | 9=278 | 31=265 | 7=265 | 14=250 | 21=244 | 19=231 | 8=198 | 6=190 | 16=175 | 15=151 | 5=150 | 18=136 | 17=125 | 11=118 | 12=108 | 13=103 | 40=100 | 10=79 | 39=73 | 35=44 | 32=35 | 33=32 | 34=31 | 60=26 | 38=26 | 36=20 | 41=14 | 61=14 | 59=10 | 47=10 | 77=6 | 111=6 | 364=6 | 42=6 | 56=6 | 65=6 | 37=4 | 153=4 | 51=4 | 55=4 | 58=4 | 45=3 | 90=2 | 91=2 | 335=2 | 46=2 | 48=2 | 227=2 | 50=2 | 52=2 | 53=2 | 57=2 | 150=2 | 66=2 | 139=2 | 79=2 | 84=2 | 88=2 | 109=2

### mv_pengawasan_ketidaksesuaian  —  9,070 rows
  - id_pengawasan                        bigint       null=        0 (  0.0%)  distinct=7259
  - id_klasifikasi                       integer      null=        0 (  0.0%)  distinct=6
  - keterangan_ketidaksesuaian           text         null=        0 (  0.0%)  distinct=6
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[id_klasifikasi] (6): 2=3,346 | 5=2,068 | 3=1,866 | 6=1,203 | 1=499 | 4=88
    VALUES[keterangan_ketidaksesuaian] (6): Iklan dengan klaim kesehatan – Iklan yang tidak sesuai dengan ketentuan=3,346 | Iklan dengan kalimat superlatif, komparatif, & mendiskreditkan (kecuali membandingkan deng=2,068 | Iklan menyesatkan karena tidak sesuai dengan karakteristik/komposisi produk=1,866 | Iklan dengan kata-kata, figure, logo, lambang yang tidak boleh diiklankan=1,203 | Iklan produk yang tidak boleh diiklankan (produk minuman beralkohol, Pangan Olahan untuk K=499 | Iklan yang melanggar norma-norma yang berlaku (adegan berbahaya, SARA, dll)=88

### mv_pengawasan_log  —  1,817,233 rows
  - id_pengawasan                        bigint       null=        0 (  0.0%)  distinct=236982
  - trx_steps                            text         null=        0 (  0.0%)  distinct=16
  - status_code                          bigint       null=        0 (  0.0%)  distinct=17
  - status_label                         text         null=    9,159 (  0.5%)  distinct=9
  - fullname                             text         null=    6,704 (  0.4%)  distinct=1536
  - nama_balai                           text         null=    6,710 (  0.4%)  distinct=90
  - catatan                              text         null=  288,140 ( 15.9%)  distinct=30551
  - tanggal_proses                       timestamp without time zone null=  302,460 ( 16.6%)  distinct=332275
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[trx_steps] (16): pusat=317,862 | draft=267,474 | spv_1_pusat=245,915 | spv_1=238,298 | kepala_balai=228,955 | direktur=190,321 | selesai=183,962 | spv_2_pusat=118,670 | spv_2=16,622 | ditolak_spv_1=5,743 | ditolak_pusat=1,705 | ditolak_spv_1_pusat=932 | ditolak_kepala_balai=411 | ditolak_spv_2=148 | ditolak_direktur=123 | ditolak_spv_2_pusat=92
    VALUES[status_code] (17): 4=317,862 | 0=267,469 | 5=245,931 | 1=238,297 | 3=228,955 | 7=190,321 | 999=183,962 | 6=118,654 | 2=16,623 | 991=5,774 | 994=1,705 | 995=932 | 993=381 | 992=148 | 997=123 | 996=92 | 990=4
    VALUES[status_label] (9): MT - Pembuatan SPK=317,862 | Operator - Draft Sampling=267,469 | Deputi MT - Pembuatan SPK=245,931 | Supervisor - Verifikasi=238,297 | TPS - Penerimaan SPU=228,955 | Penguji - Entri Hasil Pengujian=190,321 | Sampel Rujukan Selesai=183,962 | Penyelia - Pembuatan SPP=118,654 | Supervisor 2 - Verifikasi=16,623 | <NULL>=9,159

### mv_pengawasan_timeline  —  236,982 rows
  - id_pengawasan                        bigint       null=        0 (  0.0%)  distinct=236982
  - tgl_start                            date         null=        0 (  0.0%)  distinct=2384
  - tgl_end                              date         null=        0 (  0.0%)  distinct=2381
  - tanggal_kirim_kabalai                date         null=    8,446 (  3.6%)  distinct=1979
  - tanggal_kirim_direktur               date         null=   46,965 ( 19.8%)  distinct=852
  - tanggal_kirim_pusat                  date         null=    8,724 (  3.7%)  distinct=1836
  - status                               bigint       null=        0 (  0.0%)  distinct=18
  - mulai_kabalai                        integer      null=    8,446 (  3.6%)  distinct=281
  - kabalai_direktur                     integer      null=   46,965 ( 19.8%)  distinct=706
  - direktur_pusat                       integer      null=   46,965 ( 19.8%)  distinct=2
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[status] (18): 999=183,845 | 4=35,587 | 0=6,670 | 7=6,203 | 991=1,363 | 994=1,197 | 5=878 | 6=422 | 1=237 | 2=180 | 993=125 | 992=94 | 995=69 | 3=59 | 996=46 | 990=4 | 9=2 | 8=1
    VALUES[direktur_pusat] (2): 0=187,773 | <NULL>=46,965 | 1=2,244

### target_balai  —  532 rows
  - id                                   bigint       null=        0 (  0.0%)  distinct=532
  - nama_balai                           text         null=        0 (  0.0%)  distinct=76
  - komoditi                             text         null=        0 (  0.0%)  distinct=7
  - tahun                                bigint       null=        0 (  0.0%)  distinct=1
  - target_penandaan                     bigint       null=        0 (  0.0%)  distinct=253
  - target_pengawasan                    bigint       null=        0 (  0.0%)  distinct=53
  - target_pengujian                     bigint       null=        0 (  0.0%)  distinct=254
  - target_pengujian_pangan              bigint       null=       17 (  3.2%)  distinct=68
  - target_pengujian_pangan_fortifikasi  bigint       null=       17 (  3.2%)  distinct=19
  - target_sarana_distribusi             bigint       null=        0 (  0.0%)  distinct=177
  - target_sarana_produksi               bigint       null=        0 (  0.0%)  distinct=74
  - sync                                 timestamp without time zone null=        0 (  0.0%)  distinct=1
    VALUES[nama_balai] (76): BALAI BESAR POM DI PALEMBANG=7 | BALAI BESAR POM DI BANJARBARU=7 | BALAI BESAR POM DI GORONTALO=7 | BALAI POM DI TASIKMALAYA=7 | BALAI BESAR POM DI PEKANBARU=7 | BALAI BESAR POM DI SURABAYA=7 | Loka POM di Kabupaten Sijunjung=7 | Loka POM di Kabupaten Belitung=7 | BALAI BESAR POM DI PONTIANAK=7 | Loka POM di Kota Lubuklinggau=7 | BALAI BESAR POM DI KENDARI=7 | BALAI POM DI DUMAI =7 | BALAI POM DI AMBON=7 | BALAI BESAR POM DI PALU=7 | BALAI POM DI BALIKPAPAN=7 | BALAI BESAR POM DI BANDAR LAMPUNG=7 | BALAI BESAR POM DI SEMARANG=7 | Loka POM di Kabupaten Kepulauan Sangihe=7 | Loka POM di Kab. Sumba Timur=7 | BALAI BESAR POM DI SERANG=7 | BALAI BESAR POM DI MANADO=7 | Loka POM di Kab. Sambas=7 | BALAI BESAR POM DI BANDUNG=7 | Loka POM di Kab. Belu=7 | BALAI POM DI TARAKAN=7 | BALAI POM DI TANJUNGBALAI=7 | Loka POM di Kabupaten Buleleng=7 | Loka POM di Kabupaten Aceh Selatan=7 | BALAI POM DI PAYAKUMBUH=7 | BALAI POM DI JAMBI=7 | BALAI POM DI BENGKULU=7 | BALAI POM DI JEMBER=7 | BALAI BESAR POM DI BANDA ACEH=7 | BALAI POM DI BATAM=7 | BALAI POM DI TANGERANG=7 | BALAI BESAR POM DI MEDAN=7 | BALAI POM DI PALOPO=7 | BALAI POM DI TULANGBAWANG=7 | BALAI POM DI ENDE=7 | BALAI POM DI TABALONG=7 | Loka POM di Kabupaten Merauke=7 | Loka POM di Kabupaten Manggarai Barat=7 | BALAI POM DI SANGGAU=7 | BALAI POM DI MANOKWARI=7 | BALAI POM DI INDRAGIRI HULU=7 | BALAI POM DI BOGOR=7 | BALAI POM DI BAU-BAU=7 | BALAI BESAR POM DI PALANGKARAYA=7 | BALAI POM DI PANGKALPINANG=7 | BALAI POM DI SOFIFI=7 | BALAI BESAR POM DI YOGYAKARTA=7 | BALAI BESAR POM DI JAKARTA=7 | BALAI BESAR POM DI KUPANG=7 | Loka POM di Kabupaten Tanah Bumbu=7 | BALAI BESAR POM DI MATARAM=7 | BALAI BESAR POM DI SAMARINDA=7 | Loka POM di Kabupaten Banggai=7 | BALAI POM DI SURAKARTA=7 | BALAI POM DI TOBA=7 | BALAI BESAR POM DI DENPASAR=7 | Loka POM di Kabupaten Aceh Tengah=7 | BALAI BESAR POM DI PADANG=7 | Loka POM di Kabupaten Rejang Lebong=7 | BALAI POM DI KEDIRI=7 | Loka POM di Kabupaten Mimika=7 | BALAI BESAR POM DI MAKASSAR=7 | BALAI POM DI BANYUMAS=7 | BALAI BESAR POM DI JAYAPURA=7 | Loka POM di Kabupaten Kotawaringin Barat=7 | Loka POM di Kabupaten Bungo=7 | Loka POM di Kabupaten Pulau Morotai=7 | BALAI POM DI BIMA=7 | Loka POM di Kabupaten Tanimbar=7 | BALAI POM DI MAMUJU=7 | Loka POM di Kabupaten Sorong=7 | Loka POM di Kota Tanjung Pinang=7
    VALUES[komoditi] (7): Obat Kuasi=76 | Produk Pangan=76 | Obat Tradisional (OT)=76 | Obat=76 | Kosmetika=76 | Suplemen Kesehatan=76 | Rokok=76
    VALUES[tahun] (1): 2024=532
    VALUES[target_pengawasan] (53): 0=76 | 10=55 | 110=42 | 15=42 | 120=38 | 35=26 | 75=22 | 235=21 | 40=19 | 300=17 | 5=16 | 360=14 | 432=10 | 576=10 | 85=9 | 30=8 | 288=8 | 25=8 | 100=7 | 70=7 | 270=6 | 60=6 | 80=6 | 20=6 | 65=5 | 305=5 | 130=5 | 250=3 | 50=3 | 160=3 | 175=2 | 90=2 | 210=2 | 170=2 | 620=2 | 320=2 | 215=1 | 150=1 | 95=1 | 79=1 | 200=1 | 115=1 | 381=1 | 105=1 | 420=1 | 356=1 | 440=1 | 180=1 | 133=1 | 600=1 | 125=1 | 530=1 | 260=1
    VALUES[target_pengujian_pangan] (68): 0=439 | <NULL>=17 | 65=3 | 160=3 | 64=2 | 80=2 | 50=2 | 60=2 | 110=2 | 760=1 | 215=1 | 575=1 | 875=1 | 540=1 | 95=1 | 643=1 | 555=1 | 627=1 | 481=1 | 76=1 | 100=1 | 387=1 | 942=1 | 919=1 | 132=1 | 66=1 | 894=1 | 199=1 | 114=1 | 163=1 | 82=1 | 450=1 | 69=1 | 105=1 | 141=1 | 150=1 | 670=1 | 122=1 | 553=1 | 177=1 | 212=1 | 566=1 | 241=1 | 435=1 | 538=1 | 171=1 | 620=1 | 254=1 | 116=1 | 607=1 | 41=1 | 448=1 | 185=1 | 120=1 | 90=1 | 957=1 | 560=1 | 71=1 | 210=1 | 70=1 | 198=1 | 75=1 | 573=1 | 155=1 | 347=1 | 173=1 | 909=1 | 397=1 | 196=1
    VALUES[target_pengujian_pangan_fortifikasi] (19): 0=462 | <NULL>=17 | 15=10 | 75=9 | 20=6 | 60=4 | 125=4 | 70=4 | 80=3 | 50=2 | 85=2 | 31=1 | 30=1 | 65=1 | 105=1 | 110=1 | 10=1 | 100=1 | 39=1 | 40=1
    VALUES[target_sarana_produksi] (74): 0=327 | 1=38 | 2=12 | 3=11 | 4=10 | 5=7 | 12=6 | 25=6 | 6=5 | 13=5 | 21=5 | 7=4 | 11=4 | 10=4 | 33=3 | 38=3 | 40=3 | 18=3 | 31=3 | 8=3 | 28=2 | 60=2 | 23=2 | 62=2 | 9=2 | 15=2 | 30=2 | 14=2 | 65=2 | 44=2 | 36=2 | 24=2 | 17=2 | 48=2 | 22=2 | 50=2 | 16=1 | 71=1 | 26=1 | 72=1 | 70=1 | 75=1 | 96=1 | 207=1 | 144=1 | 109=1 | 19=1 | 20=1 | 34=1 | 32=1 | 261=1 | 66=1 | 175=1 | 51=1 | 153=1 | 27=1 | 190=1 | 235=1 | 43=1 | 42=1 | 309=1 | 69=1 | 54=1 | 139=1 | 55=1 | 52=1 | 85=1 | 73=1 | 164=1 | 87=1 | 124=1 | 56=1 | 35=1 | 162=1
