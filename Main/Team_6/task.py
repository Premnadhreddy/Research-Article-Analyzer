import re
from typing import List, Tuple, Optional

class team_6:
    """
    A linter to enforce IEEE title case capitalization for subsection and
    subsubsection titles in LaTeX documents.
    """
    # --- Word Lists for Capitalization Rules ---
    ARTICLES = {'a', 'an', 'the'}
    COORDINATING_CONJUNCTIONS = {'and', 'but', 'or', 'nor', 'for', 'so', 'yet'}
    SHORT_PREPOSITIONS = {
        'in', 'on', 'to', 'of', 'by', 'at', 'up', 'off', 'via', 'per', 'as', 'is',
        'for', 'out', 'but', 'nor', 'yet', 'so'
    }
    ACRONYMS = {
        "AF", "AFC", "AGC", "AM", "APD", "AR", "ARMA", "ASIC", "ASK", "ATM", "AWGN",
        "BER", "BPSK", "BWO", "CCD", "CDMA", "CD-ROM", "CIM", "CIR", "CMOS", "CPFSK",
        "CPM", "CPSK", "CPU", "CRT", "CT", "CV", "CW", "DC", "DFT", "DMA", "DPCM",
        "DPSK", "EDP", "EHF", "ELF", "EMC", "EMF", "EMI", "FDM", "FDMA", "FET", "FFT",
        "FIR", "FM", "FSK", "FTP", "FWHM", "GUI", "HBT", "HEMT", "HF", "HTML", "HV",
        "HVdc", "IC", "IDP", "IF", "IGFET", "IM", "IMPATT", "I/O", "IR", "ISI", "JFET",
        "JPEG", "LAN", "LC", "LED", "LHS", "LMS", "LO", "LP", "LPE", "LR", "MESFET",
        "MF", "MFSK", "MHD", "MIS", "MLE", "MLSE", "MMF", "MOS", "MOSFET", "MOST",
        "MPEG", "NIR", "NMR", "NRZ", "OD", "OEIC", "OOP", "PAM", "PC", "PCM", "PDF",
        "PDM", "PF", "PID", "PLL", "PM", "PML", "PP", "PPM", "PRF", "PRR", "PSK",
        "PTM", "PWM", "Q", "QoS", "QPSK", "RAM", "RC", "RF", "RFI", "RIN", "RL",
        "R&D", "RV", "SAW", "SGML", "SHF", "SI", "SIR", "S/N", "SOC", "SSB", "SW",
        "SWR", "TDM", "TDMA", "TE", "TEM", "TFT", "TM", "TVI", "TWA", "UHF", "UV",
        "VCO", "VHF", "VLSI", "WAN", "WDM", "CSI", "LWIIR", "TAS", "SEP", "SRX"
    }
    LOWERCASE_WORDS = ARTICLES | COORDINATING_CONJUNCTIONS | SHORT_PREPOSITIONS

    def __init__(self, latex_code: str, text_begin: Optional[str] = None):
        self.latex_code = latex_code

    def extract_section_titles(self) -> List[Tuple[int, str, str]]:
        """
        Extracts all subsection and subsubsection titles from the LaTeX code.
        """
        lines = self.latex_code.splitlines()
        sections = []
        pattern = re.compile(r'^\s*\\(sub(?:sub)?section)\s*\{([^}]*)\}')
        for line_num, line in enumerate(lines, 1):
            if line.strip().startswith('%'):
                continue
            match = pattern.search(line)
            if match:
                title = match.group(2).strip()
                if title:
                    sections.append((line_num, match.group(1), title))
        return sections

    def get_expected_case(self, word: str, is_first: bool, is_last: bool, after_colon: bool) -> str:
        """
        Determines the correct capitalization for a single word based on IEEE rules.
        """
        if word.upper() in self.ACRONYMS:
            return word.upper()

        if is_first or is_last or after_colon or (word.lower() not in self.LOWERCASE_WORDS):
            return word.capitalize()
        else:
            return word.lower()

    def correct_title_capitalization(self, title: str) -> str:
        """
        Applies IEEE title case rules to a full title string, intelligently
        handling LaTeX commands, math mode, and hyphenated words.
        """
        # This regex tokenizes the title into a list of segments:
        # 1. LaTeX commands (e.g., \ref{...}, \Nr)
        # 2. Math environments (e.g., $...$)
        # 3. Words (including hyphenated ones)
        # 4. Any other single character (e.g., whitespace, punctuation)
        pattern = re.compile(r'(\\(?:[a-zA-Z@]+|.)(?:\{[^}]*\})*(?:\[[^\]]*\])*|\$.*?\$|[\w\'-]+|.)')
        segments = [s for s in pattern.findall(title) if s]

        # Identify the indices of the first and last words in the segments list
        first_word_idx, last_word_idx = -1, -1
        for i, seg in enumerate(segments):
            if re.fullmatch(r"[\w'-]+", seg):
                if first_word_idx == -1:
                    first_word_idx = i
                last_word_idx = i
        
        if first_word_idx == -1:
            return title # No words to process

        corrected_segments = []
        is_after_colon = False

        for i, seg in enumerate(segments):
            if re.fullmatch(r"[\w'-]+", seg):
                is_first = (i == first_word_idx)
                is_last = (i == last_word_idx)
                
                if '-' in seg and len(seg) > 1:
                    parts = seg.split('-')
                    # First part follows normal rules. Subsequent parts are always capitalized.
                    corrected_parts = [self.get_expected_case(parts[0], is_first, False, is_after_colon)]
                    corrected_parts.extend(part.capitalize() for part in parts[1:])
                    corrected_segments.append('-'.join(corrected_parts))
                else:
                    corrected_segments.append(self.get_expected_case(seg, is_first, is_last, is_after_colon))
                
                is_after_colon = False
            else:
                corrected_segments.append(seg)
                if ':' in seg:
                    is_after_colon = True
        
        return "".join(corrected_segments)

    def run(self) -> str:
        """
        Runs all linter checks and returns a formatted report as a single string.
        """
        if not self.latex_code or not self.latex_code.strip():
            return ""

        sections = self.extract_section_titles()
        issues = []
        for line_num, section_type, title in sections:
            corrected_title = self.correct_title_capitalization(title)
            if corrected_title != title:
                issues.append(f'Line {line_num}: [Capitalization] Title should be "{corrected_title}" instead of "{title}".')

        if not issues:
            return ""

        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("Sub-Section Related Comments".center(70))
        report_lines.append("=" * 70)
        report_lines.extend(issues)
        report_lines.append("")
        
        final_report_string = '\n'.join(report_lines)

        try:
            with open("LOGII", 'w', encoding='utf-8') as log_file:
                log_file.write(final_report_string)
        except IOError as e:
            error_message = f"\nError: Could not write to log file. Reason: {e}"
            final_report_string += error_message

        return final_report_string
