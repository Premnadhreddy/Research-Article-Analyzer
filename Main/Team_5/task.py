import re
from typing import List, Optional

class team_5:
    """
    A comprehensive linter to analyze LaTeX files for common style and formatting issues,
    with a focus on IEEE typesetting standards.
    """

    def __init__(self, latex_content: str, text_begin=None, log_path: str = 'LOGII'):
        """
        Initializes the linter with LaTeX content.
        """
        self.latex_content = latex_content
        self.log_path = 'LOGII'

        # --- Pre-compiled Regex Patterns for Efficiency ---
        self.env_patterns = {
            name: re.compile(r'\\begin{' + name + r'}(.*?)\\end{' + name + r'}', re.DOTALL)
            for name in ['equation', 'align', 'multline', 'gather']
        }
        self.patterns = {
            'math_content': re.compile(r'\\begin{(?:equation|align|multline|gather|array)}.*?\\end{(?:equation|align|multline|gather|array)}|\$.*?\$|\\\(.*?\\\)', re.DOTALL),
            'eqnarray': re.compile(r'\\begin{eqnarray}'),
            'ref': re.compile(r'\\ref\{(eq:.+?)\}'),
            'blank_before_env': re.compile(r'\n\s*\n(\s*\\begin{(?:equation|align|multline|gather)})'),
            'blank_after_env': re.compile(r'(\\end{(?:equation|align|multline|gather)})\s*\n\s*\n'),
        }

    def _get_line_number_from_pos(self, pos: int) -> int:
        """Calculates the 1-based line number from a character position."""
        return self.latex_content.count('\n', 0, pos) + 1

    def _get_next_meaningful_word(self, text_chunk: str) -> Optional[str]:
        """Finds the first meaningful word, skipping comments and sectioning commands."""
        non_comment_lines = [line for line in text_chunk.split('\n') if not line.strip().startswith('%')]
        text_chunk = '\n'.join(non_comment_lines)
        words = re.findall(r'\S+', text_chunk)
        
        for word in words:
            if not word.startswith(('\\section', '\\subsection', '\\item', '\\label')):
                if word.startswith(r'{\em'):
                    return re.sub(r'[{\\}A-Za-z]+', '', word)
                return word
        return None

    # --- Linter Check Functions ---

    def check_end_of_env_punctuation(self) -> List[str]:
        """RULE: Every equation should end with a punctuation mark."""
        issues = []
        for env_name in ['equation', 'align', 'gather']:
            for match in self.env_patterns[env_name].finditer(self.latex_content):
                env_content = match.group(1)
                
                if not env_content.strip() or env_content.strip().startswith('%') or r'\nonumber' in match.group(0):
                    continue

                # First, remove the label to avoid it interfering with punctuation check
                preceding_text = re.split(r'\\label\{.*?\}', env_content)[0]
                
                # Clean the text by removing comments and trailing whitespace
                clean_text = '\n'.join([line.split('%')[0].rstrip() for line in preceding_text.split('\n')]).rstrip()
                
                if not clean_text: continue

                # Find the last non-empty line to report the correct line number
                lines_in_content = clean_text.strip().split('\n')
                last_line_content = lines_in_content[-1].strip() if lines_in_content else ''
                
                error_pos = match.start() + preceding_text.rfind(last_line_content)
                line_no = self._get_line_number_from_pos(error_pos)

                last_char = clean_text[-1]
                text_after_env = self.latex_content[match.end():]
                next_word = self._get_next_meaningful_word(text_after_env)

                if not next_word: continue

                if last_char in ['.', ',']:
                    if next_word[0].isupper() and last_char != '.':
                        issues.append(f"Line {line_no}: [Punctuation] To start a new sentence, end the equation with a period '.', not a comma.")
                    elif not next_word[0].isupper() and not next_word.startswith((r'\item', '(', '\\section', '\\subsection')) and last_char != ',':
                        issues.append(f"Line {line_no}: [Punctuation] To continue the sentence, end the equation with a comma ',', not a period.")
                else:
                    issues.append(f"Line {line_no}: [Punctuation] An equation that is part of a sentence must end with punctuation. Add a comma ',' or a period '.'")
        return list(dict.fromkeys(issues))

    def check_inter_equation_punctuation(self) -> List[str]:
        """RULE: In 'align', intermediate equations must end with a comma."""
        issues = []
        for match in self.env_patterns['align'].finditer(self.latex_content):
            content = match.group(1)
            start_pos = match.start(1)
            lines = content.strip().split(r'\\')
            
            current_pos = start_pos
            for line in lines[:-1]: # Check all lines except the last
                clean_line = line.split('%')[0].rstrip()
                if clean_line and not clean_line.endswith(','):
                    line_no = self._get_line_number_from_pos(current_pos + line.rfind(line.strip()))
                    issues.append(f"Line {line_no}: [Punctuation] To separate equations in an 'align' environment, end this line with a comma ','.")
                current_pos += len(line) + 2 # Add 2 for the '\\'
        return list(dict.fromkeys(issues))

    def check_multline_operator_placement(self) -> List[str]:
        """RULE: In 'multline', the math operator should be on the new line."""
        issues = []
        math_operators = [r'+', r'-', r'=', r'>', r'<', r'\times', r'\leq', r'\geq', r'/']
        for match in self.env_patterns['multline'].finditer(self.latex_content):
            content = match.group(1)
            start_pos = match.start(1)
            lines = content.strip().split(r'\\')
            
            current_pos = start_pos
            for i, line_content in enumerate(lines):
                line_no = self._get_line_number_from_pos(current_pos)
                stripped_line = re.sub(r'^\s*\\hspace\*?\{.*?\}\s*', '', line_content.strip())

                if i < len(lines) - 1 and any(stripped_line.endswith(op) for op in math_operators):
                    issues.append(f"Line {line_no}: [Operator Placement] For clarity, move the operator from the end of this line to the beginning of the next.")
                
                if i > 0 and stripped_line and not any(stripped_line.startswith(op) for op in math_operators):
                    issues.append(f"Line {line_no}: [Operator Placement] A new line in a 'multline' environment should start with a math operator (e.g., +, -, =).")
                
                current_pos += len(line_content) + 2
        return list(dict.fromkeys(issues))

    def check_equation_labeling(self) -> List[str]:
        """RULE: Every numbered equation must have a label."""
        issues = []
        for name, pattern in self.env_patterns.items():
            for match in pattern.finditer(self.latex_content):
                if r'\nonumber' in match.group(0): continue
                if r'\label' not in match.group(1):
                    line_no = self._get_line_number_from_pos(match.start())
                    issues.append(f"Line {line_no}: [Labeling] This '{name}' environment is missing a '\\label{{...}}'. Add one to make it referenceable.")
        return list(dict.fromkeys(issues))

    def check_equation_referencing(self) -> List[str]:
        """RULE: Use '\\eqref{}' to reference equations."""
        issues = []
        for match in self.patterns['ref'].finditer(self.latex_content):
            line_no = self._get_line_number_from_pos(match.start())
            label = match.group(1)
            issues.append(f"Line {line_no}: [Referencing] For consistency, use '\\eqref{{{label}}}' to reference equations, which adds parentheses automatically.")
        return list(dict.fromkeys(issues))

    def check_deprecated_environments(self) -> List[str]:
        """RULE: Avoid using the deprecated 'eqnarray' environment."""
        issues = []
        for match in self.patterns['eqnarray'].finditer(self.latex_content):
            line_no = self._get_line_number_from_pos(match.start())
            issues.append(f"Line {line_no}: [Environments] The 'eqnarray' environment is outdated. Replace it with 'align' for better spacing and features.")
        return list(dict.fromkeys(issues))

    def check_unicode_math_symbols(self) -> List[str]:
        """RULE: Use LaTeX commands instead of Unicode characters for math symbols."""
        issues = []
        unicode_map = {'→': r'\rightarrow', '≤': r'\leq', '≥': r'\geq', '±': r'\pm', '×': r'\times', '÷': r'\div', '≠': r'\neq'}
        for char, command in unicode_map.items():
            for match in re.finditer(re.escape(char), self.latex_content):
                line_no = self._get_line_number_from_pos(match.start())
                issues.append(f"Line {line_no}: [Symbols] Replace the Unicode character '{char}' with its LaTeX command '{command}' for document compatibility.")
        return list(dict.fromkeys(issues))

    def check_math_function_formatting(self) -> List[str]:
        """RULE: Use commands like '\\sin' for function names."""
        issues = []
        math_functions = ['sin', 'cos', 'tan', 'log', 'exp', 'det', 'lim', 'sec', 'csc', 'cot']
        for math_match in self.patterns['math_content'].finditer(self.latex_content):
            math_content = math_match.group(0)
            for func in math_functions:
                for func_match in re.finditer(r'(?<!\\)\b' + func + r'\b', math_content):
                    line_no = self._get_line_number_from_pos(math_match.start() + func_match.start())
                    issues.append(f"Line {line_no}: [Functions] For correct typographical formatting, write the function '{func}' as '\\{func}'.")
        return list(dict.fromkeys(issues))

    def check_text_in_math_mode(self) -> List[str]:
        """RULE: Use '\\text{{...}}' for words inside math mode."""
        issues = []
        text_words = ['where', 'for', 'if', 'otherwise', 'subject to', 'and', 'or']
        for math_match in self.patterns['math_content'].finditer(self.latex_content):
            math_content = math_match.group(0)
            # Create a version of the content with all \text{...} blocks removed to avoid false positives
            content_without_text = re.sub(r'\\text\{.*?\}', '', math_content)
            for word in text_words:
                for word_match in re.finditer(r'\b' + word + r'\b', content_without_text, re.IGNORECASE):
                    line_no = self._get_line_number_from_pos(math_match.start() + word_match.start())
                    issues.append(f"Line {line_no}: [Text in Math] Words in math mode should be in upright font. Wrap '{word_match.group(0)}' in '\\text{{...}}'.")
        return list(dict.fromkeys(issues))

    def check_blank_lines_around_equations(self) -> List[str]:
        """RULE: Avoid extra blank lines around equations."""
        issues = []
        for match in self.patterns['blank_before_env'].finditer(self.latex_content):
            line_no = self._get_line_number_from_pos(match.start(1))
            issues.append(f"Line {line_no}: [Spacing] Remove the blank line before this equation to maintain consistent paragraph spacing.")
        for match in self.patterns['blank_after_env'].finditer(self.latex_content):
            line_no = self._get_line_number_from_pos(match.start(1))
            issues.append(f"Line {line_no}: [Spacing] Remove the blank line after this equation to maintain consistent paragraph spacing.")
        return list(dict.fromkeys(issues))

    def check_align_character(self) -> List[str]:
        """RULE: Each line in 'align' must have an alignment character '&'."""
        issues = []
        for match in self.env_patterns['align'].finditer(self.latex_content):
            content = match.group(1)
            start_pos = match.start(1)
            lines = content.strip().split(r'\\')
            
            current_pos = start_pos
            for line in lines:
                if line.strip() and '&' not in line:
                    line_no = self._get_line_number_from_pos(current_pos + line.find(line.strip()))
                    issues.append(f"Line {line_no}: [Alignment] Add an '&' to this line to define the alignment point (e.g., place it before the '=' sign).")
                current_pos += len(line) + 2
        return list(dict.fromkeys(issues))

    def run(self) -> str:
        """
        Runs all linter checks and returns a formatted report as a single string.
        """
        if not self.latex_content.strip():
            return ""

        issue_groups = {
            "Punctuation of Equations": self.check_end_of_env_punctuation(),
            "Punctuation Within Multi-line Equations": self.check_inter_equation_punctuation(),
            "Operator Placement in Long Equations": self.check_multline_operator_placement(),
            "Equation Labeling": self.check_equation_labeling(),
            "Equation Referencing Style": self.check_equation_referencing(),
            "Use of Modern Environments": self.check_deprecated_environments(),
            "Math Symbol Formatting": self.check_unicode_math_symbols(),
            "Math Function Formatting": self.check_math_function_formatting(),
            "Text Formatting in Math Mode": self.check_text_in_math_mode(),
            "Spacing Around Equations": self.check_blank_lines_around_equations(),
            "Alignment Character in 'align'": self.check_align_character(),
        }

        report_lines = []
        
        for title, issues in issue_groups.items():
            if issues:
                report_lines.append("=" * 70)
                report_lines.append(title.center(70))
                report_lines.append("=" * 70)
                report_lines.extend(issues)
                report_lines.append("")

        if not report_lines:
            return "" # Return empty string if no issues are found

        final_report_string = '\n'.join(report_lines)

        try:
            with open(self.log_path, 'w', encoding='utf-8') as log_file:
                log_file.write(final_report_string)
        except IOError as e:
            error_message = f"\nError: Could not write to log file at '{self.log_path}'. Reason: {e}"
            final_report_string += error_message

        return final_report_string
