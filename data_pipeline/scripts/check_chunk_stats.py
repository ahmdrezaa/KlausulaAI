import json
import statistics
from pathlib import Path

def analyze_chunks(json_path: str):
    print(f"\nMenganalisis Chunk dari: {Path(json_path).name}")
    print("-" * 50)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Ambil panjang karakter dari masing-masing chunk (Pasal)
    chunk_sizes = [len(pasal['full_text']) for pasal in data]
    
    if not chunk_sizes:
        print("Data kosong!")
        return

    # Kalkulasi statistik
    total_chunks = len(chunk_sizes)
    avg_size = statistics.mean(chunk_sizes)
    max_size = max(chunk_sizes)
    min_size = min(chunk_sizes)
    
    # Cari tahu Pasal mana yang paling panjang
    longest_pasal = next(p for p in data if len(p['full_text']) == max_size)

    print(f"Total Chunks (Pasal) : {total_chunks} chunks")
    print(f"Overlap yang dipakai : 0 (Structural Chunking)")
    print(f"Rata-rata Chunk Size : {avg_size:.0f} karakter")
    print(f"Chunk Terkecil       : {min_size} karakter")
    print(f"Chunk Terbesar       : {max_size} karakter")
    print("-" * 50)
    print(f"INFO: Chunk terbesar ada di Pasal {longest_pasal['pasal_number']} "
          f"dengan {max_size} karakter.")
          
    # Estimasi Token (Asumsi kasar: 1 kata bahasa Indonesia ~ 1.5 - 2 token)
    est_max_token = max_size / 5 # Estimasi kasar karakter ke token
    print(f"Estimasi max token: ~{est_max_token:.0f} tokens.")
    print("   (Pastikan model embedding yang dipilih mendukung limit token ini).")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    target_file = BASE_DIR / "04_chunked_data" / "uu_umkm_pasal_list.json"
    
    analyze_chunks(str(target_file))