import numpy as np
import librosa

# ---------------------------------------------------------
# 1. ฐานข้อมูลตาข่ายดักจับกีตาร์ (6 สาย)
# ---------------------------------------------------------
guitar_map = [
    (320, 335, 1, 0), (340, 355, 1, 1), (360, 375, 1, 2), (382, 398, 1, 3), (405, 420, 1, 4), (430, 450, 1, 5), (455, 475, 1, 6), (485, 500, 1, 7), (515, 530, 1, 8), (545, 560, 1, 9), (575, 595, 1, 10), (610, 630, 1, 11), (650, 670, 1, 12), (690, 710, 1, 13), (730, 750, 1, 14), (770, 795, 1, 15), (815, 845, 1, 16), (860, 895, 1, 17), (910, 945, 1, 18), (970, 995, 1, 19), (1030, 1060, 1, 20), (1090, 1120, 1, 21),
    (240, 253, 2, 0), (257, 269, 2, 1), (273, 285, 2, 2), (289, 302, 2, 3), (306, 319, 2, 4), (320, 338, 2, 5), (340, 358, 2, 6), (363, 380, 2, 7), (385, 400, 2, 8), (408, 425, 2, 9), (432, 452, 2, 10), (458, 478, 2, 11), (485, 508, 2, 12), (512, 535, 2, 13), (542, 565, 2, 14), (575, 600, 2, 15), (610, 635, 2, 16), (648, 672, 2, 17), (685, 715, 2, 18), (725, 752, 2, 19), (770, 795, 2, 20), (815, 848, 2, 21),
    (195, 208, 3, 0), (210, 222, 3, 1), (223, 232, 3, 2), (234, 245, 3, 3), (247, 258, 3, 4), (260, 273, 3, 5), (275, 290, 3, 6), (292, 306, 3, 7), (308, 322, 3, 8), (325, 342, 3, 9), (345, 362, 3, 10), (368, 385, 3, 11), (388, 405, 3, 12), (408, 428, 3, 13), (435, 455, 3, 14), (458, 475, 3, 15), (485, 515, 3, 16), (525, 550, 3, 17), (552, 570, 3, 18), (585, 605, 3, 19), (612, 635, 3, 20), (642, 672, 3, 21),
    (140, 153, 4, 0), (149, 162, 4, 1), (158, 171, 4, 2), (167, 181, 4, 3), (177, 192, 4, 4), (188, 203, 4, 5), (199, 215, 4, 6), (211, 228, 4, 7), (223, 241, 4, 8), (236, 255, 4, 9), (250, 270, 4, 10), (265, 286, 4, 11), (280, 303, 4, 12),
    (105, 115, 5, 0), (111, 121, 5, 1), (118, 128, 5, 2), (125, 136, 5, 3), (132, 144, 5, 4), (140, 153, 5, 5), (149, 162, 5, 6), (158, 171, 5, 7), (167, 181, 5, 8), (177, 192, 5, 9), (188, 203, 5, 10), (199, 215, 5, 11), (211, 228, 5, 12),
    (78, 86, 6, 0), (83, 91, 6, 1), (88, 97, 6, 2), (94, 102, 6, 3), (99, 108, 6, 4), (105, 115, 6, 5), (111, 121, 6, 6), (118, 128, 6, 7), (125, 136, 6, 8), (132, 144, 6, 9), (140, 153, 6, 10), (149, 162, 6, 11), (158, 171, 6, 12)
]

def get_candidates(hz):
    return [(s, f) for min_h, max_h, s, f in guitar_map if min_h <= hz <= max_h]

def decide_best_note(candidates, last_str, last_fret):
    if len(candidates) == 1: return candidates[0]
    if last_str is None:
        candidates.sort(key=lambda x: x[0]) 
        return candidates[0]
        
    best_candidate = None
    min_distance = 9999
    for cand_str, cand_fret in candidates:
        total_distance = abs(cand_fret - last_fret) + (abs(cand_str - last_str) * 3)
        if total_distance < min_distance:
            min_distance = total_distance
            best_candidate = (cand_str, cand_fret)
    return best_candidate

def generate_tab_text(tab_seq):
    if not tab_seq:
        return "e|----------------------------------------------------|\nB|----------------------------------------------------|\nG|----------------------------------------------------|\nD|----------------------------------------------------|\nA|----------------------------------------------------|\nE|----------------------------------------------------|"

    lines = {1: "e|-", 2: "B|-", 3: "G|-", 4: "D|-", 5: "A|-", 6: "E|-"}
    for note_str, note_fret in tab_seq:
        for s in range(1, 7):
            if s == note_str:
                fret_str = str(note_fret)
                lines[s] += f"-{fret_str}-"
                if len(fret_str) == 1: lines[s] += "-" 
            else:
                lines[s] += "----"

    result = []
    for s in range(1, 7):
        lines[s] += "-|"
        result.append(lines[s])
    return "\n".join(result)

# ---------------------------------------------------------
# 2. ฟังก์ชันประมวลผลแท็บแบบวิเคราะห์ไฟล์เต็ม (Cloud Mode)
# ---------------------------------------------------------
def process_wav_file(filepath):
    try:
        # โหลดไฟล์เสียงที่หน้าเว็บส่งมาให้
        y, sr = librosa.load(filepath, sr=44100)
    except Exception as e:
        print("Error loading file:", e)
        return generate_tab_text([])

    hop_length = 512
    # จับจังหวะการดีด (Onset Detection) ทั้งเพลง
    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, backtrack=True)
    # วิเคราะห์ความถี่ (Pitch Tracking) ทั้งเพลง
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop_length)
    
    tab_sequence = []
    last_played_string = None
    last_played_fret = None
    
    # ดึงตัวโน้ตออกมาเฉพาะช่วงที่มีการดีด
    for onset_frame in onsets:
        if onset_frame >= magnitudes.shape[1]: 
            continue
        
        freq_index = magnitudes[:, onset_frame].argmax()
        pitch = pitches[freq_index, onset_frame]
        
        if pitch > 0:
            candidates = get_candidates(pitch)
            if len(candidates) > 0:
                best_str, best_fret = decide_best_note(candidates, last_played_string, last_played_fret)
                last_played_string = best_str
                last_played_fret = best_fret
                tab_sequence.append((best_str, best_fret))
                
    return generate_tab_text(tab_sequence)