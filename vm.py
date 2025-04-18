
class StackOverflowError(Exception):
    """Custom exception for stack overflow."""
    pass


class StackUnderflowError(Exception):
    """Custom exception for stack underflow."""
    pass


class VirtualMachine:
    def __init__(self, number_of_registers=4, bit_size=8, memory_size=4, verbose=False):
        if number_of_registers <= 0:
            raise ValueError("Number of registers must be at least 1")
        if bit_size <= 0:
            raise ValueError("Bit size must be at least 1")
        if memory_size < 4:
            raise ValueError("Memory size must be ≥4 for stack + I/O")
        self.verbose = verbose
        
        self.registers = {f'R{i}': 0 for i in range(number_of_registers)}
        self.bit_size = bit_size
        self.max_value = (1 << bit_size) - 1
        self.modulus = 1 << bit_size
        self.hex_digits = (bit_size + 3) // 4
        self.min_signed = -(1 << (bit_size - 1))
        self.max_signed = (1 << (bit_size - 1)) - 1

        # Memory configuration
        self.memory_size = memory_size if memory_size is not None else (1 << bit_size) # Use 'is not None' for clarity
        if self.memory_size < 4:
             raise ValueError("Memory size must be ≥4 for stack + I/O")
        self.memory = [0] * self.memory_size
        
        # Reserve I/O addresses explicitly
        self.io_output_addr = self.memory_size - 1
        self.io_input_addr = self.memory_size - 2
        self.stack_base = self.memory_size - 3
        self.stack_limit = 0  # Or set a stack size limit

        # Stack Pointer: Start 2 addresses below I/O area
        self.sp = self.stack_base
        
        # Status flags
        self.flags = {
            'Zero': False,
            'Carry': False,
            'Overflow': False,
            'Error': False
        }
        
        self.operations = {
            'INC': self.inc,
            'DEC': self.dec,
            'MOV': self.mov,
            'ROR': self.ror,
            'ROL': self.rol,
            'NOT': self.not_op,
            'OR': self.or_op,
            'AND': self.and_op,
            'XOR': self.xor_op,
            'ADD': self.add_op,
            'SUB': self.sub_op,
            'MUL': self.mul_op,
            'DIV': self.div_op,
            'MOD': self.mod_op,
            'LDA': self.lda,
            'STA': self.sta,
            'PUSH': self.push,
            'POP': self.pop,
            'IN': self.in_op,
            'OUT': self.out_op,
            'CMP': self.cmp_op,
            'SHL': self.shl,
            'SHR': self.shr
        }

    def _to_signed(self, value):
        """Convert stored value to signed integer"""
        return value if value <= self.max_signed else value - self.modulus

    def _update_zero(self, value):
        """Update Zero flag based on value"""
        self.flags['Zero'] = (value == 0)

    def _get_value(self, src):
        """Resolve register or numeric value with hex/bin support"""
        if src in self.registers:
            return self.registers[src]
        
        try:
            src_lower = src.lower()
            base = 10
            if src_lower.startswith('0x'):
                base = 16
                src_clean = src_lower[2:]
            elif src_lower.startswith('0b'):
                base = 2
                src_clean = src_lower[2:]
            else:
                src_clean = src_lower

            value = int(src_clean, base)
            return value % self.modulus
        except ValueError:
            raise ValueError(f"Invalid value: {src}")

    def _resolve_address(self, address_src):
        """Convert address source to valid memory index"""
        address = self._get_value(address_src)
        return address % self.memory_size

    def _format_bits(self, value):
        """Format value as binary string with proper bit length"""
        return format(value, f'0{self.bit_size}b')

    def print_state(self, show_memory=8):
        """Enhanced display with binary visualization"""
        print(f"\nRegisters ({self.bit_size}-bit):")
        for reg, value in self.registers.items():
            bits = self._format_bits(value)
            highlighted = ' '.join(bits)  # Add spaces between bits
            print(f"{reg}: {value:4d} (0x{value:0{self.hex_digits}X} | {highlighted})")
        
        print("\nStatus flags:")
        for flag, state in self.flags.items():
            print(f"  {flag}: {state}")
        
        print(f"\nFirst {show_memory} memory locations:")
        for i in range(show_memory):
            val = self.memory[i]
            bits = self._format_bits(val)
            highlighted = ' '.join(bits)
            print(f"  [{i:03d}]: {val:4d} (0x{val:0{self.hex_digits}X} | {highlighted})")

    def validate_register(self, reg):
        return reg.upper() in self.registers  # Case-insensitive check

    # New memory operations
    def load_program(self, filename):
        """Load program from file with comment support"""
        program = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.split(';')[0].strip()  # Remove comments
                if line:
                    program.append(line)
        return program

    def save_memory_dump(self, filename, fmt='hex'):
        """Save memory contents to file"""
        with open(filename, 'w') as f:
            for addr in range(self.memory_size):
                val = self.memory[addr]
                if fmt == 'hex':
                    line = f"{addr:04X}: {val:02X}\n"
                else:
                    line = f"{addr}: {val}\n"
                f.write(line)

    def load_memory_dump(self, filename, fmt='hex'):
        """Load memory contents from file"""
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    if fmt == 'hex':
                        addr_part, val_part = line.split(':')
                        addr = int(addr_part.strip(), 16)
                        value = int(val_part.strip(), 16)
                    else:
                        addr, value = map(int, line.split(':'))
                    
                    if 0 <= addr < self.memory_size:
                        self.memory[addr] = value % self.modulus
                except:
                    continue

    def sta(self, address_dest, src):
        """Enhanced STA with I/O handling"""
        addr = self._resolve_address(address_dest)
        value = self._get_value(src)

        if addr == self.io_output_addr:
            # Character output
            self._io_write(value)
        else:
            # Normal memory write
            self.memory[addr] = value

    def lda(self, dest_reg, address_src):
        """Enhanced LDA with I/O handling"""
        addr = self._resolve_address(address_src)

        if addr == self.io_input_addr:
            # Character input
            value, _ = self._io_read()
            self.registers[dest_reg] = value % self.modulus
        else:
            # Normal memory read
            self.registers[dest_reg] = self.memory[addr]

        self._update_zero(self.registers[dest_reg])

    def _preprocess_labels(self, program):
        """Orchestrate label processing through discrete steps"""
        labels, processed = self._collect_labels(program)
        return self._resolve_references(processed, labels)

    def _collect_labels(self, program):
        """First pass: identify labels and their locations"""
        labels = {}
        processed = []

        for line in program:
            clean_line = self._clean_line(line)
            if not clean_line:
                continue

            label, instruction = self._extract_label(clean_line)
            if label:
                labels[label] = len(processed)

            if instruction:
                processed.append(self._normalize_instruction(instruction))

        return labels, processed

    def _resolve_references(self, processed, labels):
        """Second pass: replace label references with line numbers"""
        resolved_program = []
        for line in processed:
            parts = line.replace(',', ' ').split()
            if not parts:
                continue
                
            operation = parts[0]
            resolved_args = [
                self._process_argument(arg, labels) 
                for arg in parts[1:]
            ]
            resolved_program.append(' '.join([operation] + resolved_args))
            
        return resolved_program

    def _clean_line(self, line):
        """Remove comments and normalize whitespace"""
        return line.split(';')[0].strip().upper()

    def _extract_label(self, line):
        """Separate label from instruction if present"""
        if ':' not in line:
            return None, line
            
        label_part, _, instr_part = line.partition(':')
        return label_part.strip(), instr_part.strip()

    def _process_argument(self, arg, labels):
        """Resolve individual argument to final form"""
        if arg in labels:
            return str(labels[arg])
        if self.validate_register(arg):
            return arg.upper()
        return self._normalize_literal(arg)

    def _normalize_instruction(self, instr):
        """Ensure consistent formatting for instructions"""
        return ' '.join([part.upper() if part in self.operations else part 
                        for part in instr.split()])

    def _normalize_literal(self, value):
        """Standardize numeric literals to lowercase"""
        try:
            # Handle hex/bin prefixes
            if value.startswith(('0X', '0B')):
                prefix = value[:2].lower()
                digits = value[2:]
                return prefix + digits
            return value.lower()
        except AttributeError:
            return value

    def _io_read(self):
        """Reads a character from standard input"""
        try:
            char = input("\nInput > ")[0]
            value = ord(char)
            return value, char
        except IndexError:
            print("\nInput Error: No character entered. Using default value 0.", flush=True)
            return 0, None
        except Exception as e:
            print(f"\nInput Error ({type(e).__name__}). Using default value 0.", flush=True)
            return 0, None

    def _io_write(self, value):
        """Writes a character to standard output."""
        try:
            char_to_print = chr(value)
        except ValueError:
            char_to_print = '?' # Or some other placeholder
            if self.verbose:
                print(f"\nOutput Warning: Value {value} out of range for chr(). Printing '?'.", end='', flush=True)

        if self.verbose:
            printable_char = char_to_print if 32 <= value <= 126 else f'\\x{value:02X}'
            if 'Warning' not in locals() or not self.verbose:
                 print(f"\n  Output: {value} → '{printable_char}'", end='', flush=True)
        else:
            print(char_to_print, end='', flush=True)

    # --- Operation Implementations ---
    def inc(self, reg):
        original = self.registers[reg]
        self.flags['Carry'] = (original == self.max_value)
        self.registers[reg] = (original + 1) % self.modulus
        self._update_zero(self.registers[reg])
        original_signed = self._to_signed(original)
        self.flags['Overflow'] = (original_signed == self.max_signed)

    def dec(self, reg):
        original = self.registers[reg]
        self.registers[reg] = (original - 1) % self.modulus
        self._update_zero(self.registers[reg])
        original_signed = self._to_signed(original)
        self.flags['Overflow'] = (original_signed == self.min_signed)

    def mov(self, dest, src):
        if src in self.registers:
            self.registers[dest] = self.registers[src]
        else:
            self.registers[dest] = self._get_value(src)

    def ror(self, reg, count):
        value = self.registers[reg]
        count = count % self.bit_size  # Normalize shift count
        if count == 0:
            new_value = value
        else:
            mask = (1 << count) - 1
            shifted_out = value & mask
            new_value = (value >> count) | (shifted_out << (self.bit_size - count))
            # Carry is the last bit shifted out (bit at count - 1)
            carry_bit = (value >> (count - 1)) & 1
            self.flags['Carry'] = bool(carry_bit)
        self.registers[reg] = new_value
        self._update_zero(new_value)

    def rol(self, reg, count):
        value = self.registers[reg]
        count = count % self.bit_size  # Normalize shift count
        if count == 0:
            new_value = value
        else:
            shifted_out = (value >> (self.bit_size - count))  # Bits that wrap around
            new_value = ((value << count) | shifted_out) & self.max_value
            # Carry is the last bit shifted out (bit at bit_size - count)
            carry_bit = (value >> (self.bit_size - count)) & 1
            self.flags['Carry'] = bool(carry_bit)
        self.registers[reg] = new_value
        self._update_zero(new_value)

    def shl(self, reg, count):
        value = self.registers[reg]
        count = count % self.bit_size  # Normalize shift count
        if count == 0:
            new_value = value
            carry = 0
        else:
            new_value = (value << count) & self.max_value  # Apply bit mask
            carry = (value >> (self.bit_size - count)) & 1  # Last shifted-out bit
        self.registers[reg] = new_value
        self.flags['Carry'] = bool(carry)
        self._update_zero(new_value)

    def shr(self, reg, count):
        value = self.registers[reg]
        count = count % self.bit_size
        if count == 0:
            new_value = value
            carry = 0
        else:
            new_value = value >> count
            carry = (value >> (count - 1)) & 1  # Last shifted-out bit
        self.registers[reg] = new_value
        self.flags['Carry'] = bool(carry)
        self._update_zero(new_value)

    def not_op(self, reg):
        self.registers[reg] = (~self.registers[reg]) & self.max_value
        self._update_zero(self.registers[reg])

    def or_op(self, dest, src):
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] | src_val) & self.max_value
        self._update_zero(self.registers[dest])

    def and_op(self, dest, src):
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] & src_val) & self.max_value
        self._update_zero(self.registers[dest])

    def xor_op(self, dest, src):
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] ^ src_val) & self.max_value
        self._update_zero(self.registers[dest])

    def add_op(self, dest, src):
        a = self.registers[dest]
        b = self._get_value(src)
        result = a + b
        self.registers[dest] = result % self.modulus
        self.flags['Carry'] = result > self.max_value
        self._update_zero(self.registers[dest])
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        sum_signed = a_signed + b_signed
        self.flags['Overflow'] = not (self.min_signed <= sum_signed <= self.max_signed)

    def sub_op(self, dest, src):
        a = self.registers[dest]
        b = self._get_value(src)
        result = a - b
        self.registers[dest] = result % self.modulus
        self.flags['Carry'] = a < b  # Borrow flag
        self._update_zero(self.registers[dest])
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        diff_signed = a_signed - b_signed
        self.flags['Overflow'] = not (self.min_signed <= diff_signed <= self.max_signed)

    def mul_op(self, dest, src):
        a = self.registers[dest]
        b = self._get_value(src)
        result = a * b
        self.registers[dest] = result % self.modulus
        self.flags['Carry'] = result > self.max_value
        self._update_zero(self.registers[dest])
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        product_signed = a_signed * b_signed
        self.flags['Overflow'] = not (self.min_signed <= product_signed <= self.max_signed)

    def div_op(self, dest, src):
        a = self.registers[dest]
        b = self._get_value(src)
        if b == 0:
            self.flags['Error'] = True
            raise ValueError("Division by zero")
        self.registers[dest] = (a // b) % self.modulus
        self._update_zero(self.registers[dest])

    def mod_op(self, dest, src):
        a = self.registers[dest]
        b = self._get_value(src)
        if b == 0:
            self.flags['Error'] = True
            raise ValueError("Modulus by zero")
        self.registers[dest] = (a % b) % self.modulus
        self._update_zero(self.registers[dest])

    def push(self, src):
        """Push value onto stack"""
        if self.sp == self.stack_limit:
            raise StackOverflowError(f"Stack overflow: SP ({self.sp}) cannot go below stack limit ({self.stack_limit})")
        value = self._get_value(src)
        self.sp = (self.sp - 1) % self.memory_size
        self.memory[self.sp] = value
        print(f"  Stack: Pushed {value} to address {self.sp}")

    def pop(self, dest):
        """Pop value from stack"""
        if not self.validate_register(dest):
            raise ValueError(f"Invalid register: {dest}")
        if self.sp == self.stack_base:
            raise StackUnderflowError("Stack collided with I/O reserved memory")
        value = self.memory[self.sp]
        self.registers[dest] = value
        self.sp = (self.sp + 1) % self.memory_size
        print(f"  Stack: Popped {value} from address {self.sp-1}")
        self._update_zero(value)

    def in_op(self, dest_reg):
        """Input from I/O device to register"""
        if not self.validate_register(dest_reg):
            raise ValueError(f"Invalid register: {dest_reg}")

        value, char = self._io_read()

        self.registers[dest_reg] = value % self.modulus
        self._update_zero(self.registers[dest_reg])

    def out_op(self, src):
        """Output from register/immediate to I/O device"""
        value = self._get_value(src)
        self._io_write(value)

    def cmp_op(self, src1, src2):
        """Compare two values and set flags"""
        a = self._get_value(src1)
        b = self._get_value(src2)
        result = a - b
        
        # Set Zero flag
        self.flags['Zero'] = (result % self.modulus) == 0
        
        # Set Carry flag (unsigned borrow)
        self.flags['Carry'] = a < b  # Unsigned comparison
        
        # Set Overflow flag (signed overflow)
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        diff_signed = a_signed - b_signed
        self.flags['Overflow'] = not (self.min_signed <= diff_signed <= self.max_signed)

    def execute(self, program_source):
        """Execute program with full stack and subroutine support"""
        if isinstance(program_source, str):
            program = self.load_program(program_source)
        else:
            program = program_source

        processed_program = self._preprocess_labels(program)
        pc = 0
        self.flags['Error'] = False
        
        if self.verbose:
            print("Program start")
            self.print_state()
        
        while pc < len(processed_program):
            line_num = pc + 1
            instruction = processed_program[pc]
            if not instruction.strip():
                pc += 1
                continue
                
            try:
                parts = instruction.replace(',', ' ').split()
                op = parts[0].upper()
                args = parts[1:]
                
                if op == 'HLT':
                    if self.verbose:
                        print(f"\nExecution halted at line {line_num}")
                    return
                
                # Handle subroutine calls
                if op == 'CALL':
                    if len(args) != 1:
                        raise ValueError("CALL requires 1 argument")
                    
                    # Push return address (next instruction)
                    return_address = pc + 1
                    self.push(str(return_address))
                    
                    # Jump to target
                    try:
                        target_line = int(args[0])
                        if not (0 <= target_line <= len(processed_program)):
                            raise ValueError
                        pc = target_line
                    except:
                        raise ValueError(f"Invalid target line: {args[0]}")
                    
                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue
                
                # Handle returns
                if op == 'RET':
                    if len(args) != 0:
                        raise ValueError("RET requires no arguments")

                    try:
                       return_address = self.memory[self.sp]
                       self.sp = (self.sp + 1) % self.memory_size

                       if not (0 <= return_address < len(processed_program)):
                           raise ValueError(f"Invalid return address: {return_address}")

                       pc = return_address
                    except StackUnderflowError:
                         raise
                    except IndexError:
                         raise ValueError(f"Invalid stack pointer location: {self.sp}")

                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue
                
                # Handle jumps
                if op in ['JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO', 'JMP']:
                    if len(args) != 1:
                        raise ValueError(f"Invalid arguments for {op}")
                    
                    try:
                        target_line = int(args[0])
                        if not (0 <= target_line <= len(processed_program)):
                            raise ValueError
                    except:
                        raise ValueError(f"Invalid target line: {args[0]}")
                    
                    jump = False
                    if op == 'JZ': jump = self.flags['Zero']
                    elif op == 'JNZ': jump = not self.flags['Zero']
                    elif op == 'JC': jump = self.flags['Carry']
                    elif op == 'JNC': jump = not self.flags['Carry']
                    elif op == 'JO': jump = self.flags['Overflow']
                    elif op == 'JNO': jump = not self.flags['Overflow']
                    elif op == 'JMP': jump = True
                    
                    if jump:
                        pc = target_line
                    else:
                        pc += 1
                    
                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue

                # Handle memory operations
                elif op in ['LDA', 'STA']:
                    if len(args) != 2:
                        raise ValueError(f"{op} requires 2 arguments")
                        
                    if op == 'LDA':
                        dest_reg, addr_src = args
                        if not self.validate_register(dest_reg):
                            raise ValueError(f"Invalid register: {dest_reg}")
                        self.lda(dest_reg, addr_src)
                    else:  # STA
                        addr_dest, src = args
                        self.sta(addr_dest, src)
                    
                    pc += 1
                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue

                # Handle I/O operations
                elif op in ['IN', 'OUT']:
                    if len(args) != 1:
                        raise ValueError(f"{op} requires exactly 1 argument, got {len(args)}")

                    arg = args[0] # Get the single argument

                    if op == 'IN':
                        # IN requires a register
                        if not self.validate_register(arg):
                            raise ValueError(f"{op} requires a register argument, got {arg}")
                        self.in_op(arg.upper()) # Ensure uppercase register is passed

                    elif op == 'OUT':
                        # OUT can take a register or a literal.
                        # The validation/conversion happens inside self.out_op via _get_value
                        self.out_op(arg) # Pass the argument directly for _get_value to handle

                    pc += 1
                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue # Continue to next instruction after handling I/O

                elif op == 'CMP':
                    if len(args) != 2:
                        raise ValueError(f"CMP requires exactly 2 arguments (got {len(args)})")
                    
                    # Validate arguments before processing
                    valid_args = []
                    for arg in args:
                        if self.validate_register(arg) or self._is_valid_literal(arg):
                            valid_args.append(arg)
                        else:
                            raise ValueError(f"Invalid CMP argument: {arg}")
                    
                    self.cmp_op(valid_args[0], valid_args[1])
                    pc += 1
                    if self.verbose:
                        print(f"\nAfter line {line_num}: {instruction}")
                        self.print_state()
                    continue

                # Handle Stack operations (PUSH and POP)
                elif op == 'PUSH':
                    if len(args) != 1:
                        raise ValueError(f"PUSH requires exactly 1 argument, got {len(args)}")
                    self.push(args[0]) # push method resolves the source value
                    pc += 1
                    if self.verbose:
                         print(f"\nAfter line {line_num}: {instruction}")
                         self.print_state()
                    continue

                elif op == 'POP':
                    if len(args) != 1:
                        raise ValueError(f"POP requires exactly 1 argument, got {len(args)}")
                    dest_reg = args[0]
                    if not self.validate_register(dest_reg):
                        raise ValueError(f"POP requires a register argument, got {dest_reg}")
                    self.pop(dest_reg.upper()) # pop method assigns to register
                    pc += 1
                    if self.verbose:
                         print(f"\nAfter line {line_num}: {instruction}")
                         self.print_state()
                    continue

                elif op in ['ROR', 'ROL', 'SHL', 'SHR']:  # Added SHL/SHR to this group
                    if len(args) != 2:
                        raise ValueError(f"{op} requires 2 arguments: register and shift count")
                    reg = args[0]
                    if not self.validate_register(reg):
                        raise ValueError(f"Invalid register: {reg}")
                    shift_arg = args[1]
                    shift_count = self._get_value(shift_arg)
                    self.operations[op](reg, shift_count)
                                
                # Handle other operations
                if op not in self.operations:
                    raise ValueError(f"Invalid operation: {op}")
                
                # Execute operation
                if op in ['INC', 'DEC', 'NOT']:
                    if len(args) != 1:
                        raise ValueError(f"Invalid arguments for {op}")
                    reg = args[0]
                    if reg not in self.registers:
                        raise ValueError(f"Invalid register: {reg}")
                    self.operations[op](reg)
                elif op in ['MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'OR', 'AND', 'XOR']:
                    if len(args) != 2:
                        raise ValueError(f"Invalid arguments for {op}")

                    dest, src = args[0], args[1]

                    # --- MODIFICATION START ---
                    # Ensure the destination operand is a valid register name
                    if not self.validate_register(dest):
                         raise ValueError(f"Invalid destination register: {dest}")
                    dest_reg_name = dest.upper() # Normalize case after validation
                    # --- MODIFICATION END ---

                    # Use the validated and normalized register name
                    self.operations[op](dest_reg_name, src)
                
                pc += 1
                if self.verbose:
                    print(f"\nAfter line {line_num}: {instruction}")
                    self.print_state()
            
            except Exception as e:
                raise e
                if self.verbose:
                    print(f"Error at line {line_num}: {str(e)}")
                self.flags['Error'] = True
                return

    def _is_valid_literal(self, value):
        """Check if a value is a valid numeric literal"""
        try:
            self._get_value(value)
            return True
        except ValueError:
            return False


# Example Usage
if __name__ == "__main__":
    print("=== Virtual Machine Demonstration ===")
    vm = VirtualMachine(number_of_registers=4, bit_size=8, memory_size=256, verbose=False)

    program_source = vm.load_program("fibonacci.asm")

    print("\nStarting VM execution...")
    vm.execute(program_source)
    print("\nExecution finished.")