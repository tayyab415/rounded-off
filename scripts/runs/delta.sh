. ~/.lexsi_env; cd ~/work; . ~/envA/bin/activate; mkdir -p results
python delta_survival.py results/delta_w4g128.json ckpt/M1_drift ckpt/R_wise50 ckpt/R_resta10 ckpt/R_resta25 ckpt/R_lox_r8 --bits 4 --group 128
python delta_survival.py results/delta_w3g32.json ckpt/M1_drift ckpt/R_wise50 ckpt/R_resta10 ckpt/R_resta25 ckpt/R_lox_r8 --bits 3 --group 32
