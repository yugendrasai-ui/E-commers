import sys

def check_braces(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    stack = []
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        for char_pos, char in enumerate(line, 1):
            if char == '{':
                stack.append(('{', line_num, char_pos))
            elif char == '}':
                if not stack:
                    print(f"Extra closing brace at Line {line_num}, Pos {char_pos}")
                    return False
                stack.pop()
    
    if stack:
        for char, line_num, char_pos in stack:
            print(f"Unclosed opening brace at Line {line_num}, Pos {char_pos}")
        return False
    
    print("Braces are balanced.")
    return True

if __name__ == "__main__":
    check_braces(sys.argv[1])
