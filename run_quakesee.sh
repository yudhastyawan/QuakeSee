#!/usr/bin/env bash

# Dapatkan path absolut dari direktori tempat script ini berada
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Jalankan menggunakan zsh interaktif agar fungsi init_conda_intel (dari ~/.zshrc) bisa terbaca
zsh -i -c "
  echo 'Memulai QuakeSee...'
  cd \"$DIR\" || exit
  
  echo 'Menginisialisasi Conda (Intel mode)...'
  init_conda_intel
  
  echo 'Mengaktifkan environment...'
  conda activate ./env
  
  echo 'Menjalankan program...'
  python quakesee.py
"
