#!/bin/bash

# Script untuk mem-build paket Conda QuakeSee secara otomatis dan cepat
# Menggunakan lingkungan Miniforge yang terisolasi dari base Conda Anda untuk menghindari "stuck/solving environment"

set -e

BUILDER_DIR="$HOME/.miniforge_builder"
RECIPE_DIR="conda-recipe"
OUTPUT_DIR="build_output"

echo "=========================================================="
echo "      Mempersiapkan Pabrik Build QuakeSee (Miniforge)     "
echo "=========================================================="

# 1. Cek apakah Miniforge khusus build sudah terinstal
if [ ! -d "$BUILDER_DIR" ]; then
    echo ">> Miniforge builder belum ditemukan. Mengunduh dan menginstal di $BUILDER_DIR..."
    curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
    bash Miniforge3-MacOSX-x86_64.sh -b -p "$BUILDER_DIR"
    rm Miniforge3-MacOSX-x86_64.sh
    
    echo ">> Menginstal conda-build dan anaconda-client..."
    source "$BUILDER_DIR/bin/activate"
    conda install -y conda-build anaconda-client
else
    echo ">> Miniforge builder sudah tersedia di $BUILDER_DIR."
fi

# 2. Aktifkan environment builder
echo ">> Mengaktifkan environment builder..."
source "$BUILDER_DIR/bin/activate"

# 3. Mulai proses build
echo ">> Memulai proses conda build untuk $RECIPE_DIR..."
conda build "$RECIPE_DIR/" -c conda-forge

# 4. Salin hasil build (file .conda atau .tar.bz2) ke direktori saat ini
echo ">> Menyalin file hasil build ke direktori proyek..."
cp "$BUILDER_DIR"/conda-bld/noarch/quakesee-*.conda ./ 2>/dev/null || true
cp "$BUILDER_DIR"/conda-bld/noarch/quakesee-*.tar.bz2 ./ 2>/dev/null || true

echo "=========================================================="
echo " BUILD SELESAI! 🎉"
echo " File paket (quakesee-*.conda) telah disalin ke folder ini."
echo " "
echo " Langkah selanjutnya untuk rilis:"
echo " 1. $BUILDER_DIR/bin/anaconda login"
echo " 2. $BUILDER_DIR/bin/anaconda upload quakesee-<versi>.conda"
echo "=========================================================="
