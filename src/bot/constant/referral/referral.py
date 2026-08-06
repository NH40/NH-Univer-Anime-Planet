from __future__ import annotations

# Значения transactions.reason для наград личной реферальной системы (не путать с
# TRANSACTION_REASON_DONATE — тот на самом донатере, эти два — на РЕФЕРЕРЕ).
TRANSACTION_REASON_REFERRAL_REWARD = "referral_reward"
TRANSACTION_REASON_REFERRAL_DONATE_CUT = "referral_donate_cut"

# Префикс персонального диплинка (t.me/<bot>?start=r_<user_id>) — отдельно от "ref_"
# (именные кампании админа, см. constant/admin), чтобы handlers/start мог различить их.
REFERRAL_DEEPLINK_PREFIX = "r_"
