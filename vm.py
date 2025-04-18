import sys # Added for potential future use, e.g., stderr

# --- Custom Exceptions ---
class StackOverflowError(Exception):
    """Custom exception for stack overflow."""
    pass

class StackUnderflowError(Exception):
    """Custom exception for stack underflow."""
    pass

# --- Virtual Machine Class ---
class VirtualMachine:

    # --- Initialization ---
    def __init__(self, number_of_registers=4, bit_size=8, memory_size=None, verbose=False):
        """Initialize the Virtual Machine state."""
        # Input validation
        if number_of_registers <= 0:
            raise ValueError("Number of registers must be at least 1")
        if bit_size <= 0:
            raise ValueError("Bit size must be at least 1")
        # Defer memory_size check until after potential default calculation

        self.verbose = verbose

        # Register setup
        self.registers = {f'R{i}': 0 for i in range(number_of_registers)}

        # Bit size and derived limits
        self.bit_size = bit_size
        self.max_value = (1 << bit_size) - 1
        self.modulus = 1 << bit_size
        self.hex_digits = (bit_size + 3) // 4
        self.min_signed = -(1 << (bit_size - 1))
        self.max_signed = (1 << (bit_size - 1)) - 1

        # Memory configuration
        # Use 'is not None' for clarity when checking default parameter
        effective_memory_size = memory_size if memory_size is not None else (1 << bit_size)
        # Check memory size constraint (must be done after calculating effective size)
        if effective_memory_size < 4:
             raise ValueError("Memory size must be >= 4 to accommodate stack base and I/O addresses.")
        self.memory_size = effective_memory_size
        self.memory = [0] * self.memory_size

        # Reserved Memory Map (Top-down: Output, Input, Stack Base)
        self.io_output_addr = self.memory_size - 1
        self.io_input_addr = self.memory_size - 2
        self.stack_base = self.memory_size - 3
        # Stack limit (bottom boundary, stack grows downwards towards it)
        self.stack_limit = 0  # Default: stack can grow down to address 0

        # Stack Pointer Initialization
        self.sp = self.stack_base

        # Status flags
        self.flags = {
            'Zero': False,      # Result is zero
            'Carry': False,     # Unsigned overflow / borrow / last bit shifted out
            'Overflow': False,  # Signed overflow
            'Error': False      # Operation error (e.g., div by zero)
        }

        # Operation Dispatch Table (Maps instruction string to method)
        self.operations = {
            # Arithmetic
            'INC': self.inc,
            'DEC': self.dec,
            'ADD': self.add_op,
            'SUB': self.sub_op,
            'MUL': self.mul_op,
            'DIV': self.div_op,
            'MOD': self.mod_op,
            # Logic
            'NOT': self.not_op,
            'OR': self.or_op,
            'AND': self.and_op,
            'XOR': self.xor_op,
            # Shift/Rotate
            'ROR': self.ror,
            'ROL': self.rol,
            'SHL': self.shl,
            'SHR': self.shr,
            # Data Movement
            'MOV': self.mov,
            # Memory Access
            'LDA': self.lda,
            'STA': self.sta,
            # Stack
            'PUSH': self.push,
            'POP': self.pop,
            # I/O
            'IN': self.in_op,
            'OUT': self.out_op,
            # Comparison
            'CMP': self.cmp_op,
            # Control flow ops (like JMP, CALL, RET, HLT) are handled directly in execute()
        }

    # --- Public Interface & Execution ---

    def execute(self, program_source):
        """
        Execute a program provided as a list of instructions or a filename.

        Handles instruction fetching, decoding, dispatching, control flow (jumps, calls, ret),
        and error handling during execution.
        """
        if isinstance(program_source, str):
            try:
                program = self.load_program(program_source)
            except FileNotFoundError:
                print(f"Error: Program file not found: {program_source}", file=sys.stderr)
                self.flags['Error'] = True
                return
        else:
            program = list(program_source) # Ensure it's a mutable list

        # Preprocess labels into addresses/line numbers
        processed_program = self._preprocess_labels(program)
        program_len = len(processed_program)

        pc = 0 # Program Counter initialized to the start
        self.flags['Error'] = False # Reset error flag for new execution

        if self.verbose:
            print("--- Program Execution Start ---")
            self.print_state()

        # Main execution loop
        while 0 <= pc < program_len:
            line_num_display = pc + 1 # For user messages (1-based)
            instruction = processed_program[pc]

            if not instruction.strip(): # Skip blank lines potentially left by preprocessing
                pc += 1
                continue

            if self.verbose:
                print(f"\n[PC:{pc:03d}] Executing line {line_num_display}: {instruction}")

            try:
                parts = instruction.replace(',', ' ').split()
                op = parts[0].upper()
                args = parts[1:]
                current_pc = pc # Store pc before potential modification

                # --- Direct Handling for Control Flow & Special Ops ---
                if op == 'HLT':
                    if self.verbose:
                        print(f"\n--- Execution halted at line {line_num_display} (HLT) ---")
                    return # Stop execution

                elif op == 'CALL':
                    if len(args) != 1: raise ValueError("CALL requires 1 argument (target address/label)")
                    target_pc = int(self._process_argument(args[0], {})) # Process arg to get target PC
                    if not (0 <= target_pc < program_len): raise ValueError(f"CALL target out of bounds: {target_pc}")
                    return_address = current_pc + 1 # Address of the instruction *after* CALL
                    self.push(str(return_address)) # Push return address onto stack
                    pc = target_pc # Jump to target
                    if self.verbose: self.print_state()
                    continue # Skip default PC increment

                elif op == 'RET':
                    if len(args) != 0: raise ValueError("RET requires no arguments")
                    # Pop return address (assumes pop handles underflow)
                    # Need a temporary register or way to pop without one...
                    # Let's pop into a temporary variable within execute context
                    if self.sp == self.stack_base: raise StackUnderflowError("RET failed: Stack is empty")
                    return_address = self.memory[self.sp]
                    self.sp = (self.sp + 1) % self.memory_size
                    if self.verbose: print(f"  Stack: Popped return address {return_address} from { (self.sp - 1 + self.memory_size) % self.memory_size }")
                    # Validate and jump
                    if not (0 <= return_address < program_len): raise ValueError(f"Invalid return address popped: {return_address}")
                    pc = return_address
                    if self.verbose: self.print_state()
                    continue # Skip default PC increment

                elif op in ['JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO']:
                    if len(args) != 1: raise ValueError(f"{op} requires 1 argument (target address/label)")
                    target_pc = int(self._process_argument(args[0], {})) # Process arg to get target PC
                    if not (0 <= target_pc < program_len): raise ValueError(f"{op} target out of bounds: {target_pc}")

                    jump = False
                    if op == 'JMP': jump = True
                    elif op == 'JZ': jump = self.flags['Zero']
                    elif op == 'JNZ': jump = not self.flags['Zero']
                    elif op == 'JC': jump = self.flags['Carry']
                    elif op == 'JNC': jump = not self.flags['Carry']
                    elif op == 'JO': jump = self.flags['Overflow']
                    elif op == 'JNO': jump = not self.flags['Overflow']

                    if jump:
                        pc = target_pc
                        if self.verbose: print(f"  Jump taken to PC {pc}")
                        if self.verbose: self.print_state()
                        continue # Skip default PC increment
                    else:
                        if self.verbose: print(f"  Jump condition false, continuing to next instruction")
                        pc += 1 # Condition not met, proceed normally

                # --- Dispatching to Operation Methods ---
                elif op in self.operations:
                    op_method = self.operations[op]
                    # Argument count and type validation based on operation type
                    if op in ['INC', 'DEC', 'NOT']: # Require 1 register arg
                        if len(args) != 1: raise ValueError(f"{op} requires 1 register argument")
                        reg = args[0]
                        if not self.validate_register(reg): raise ValueError(f"Invalid register for {op}: {reg}")
                        op_method(reg.upper())
                    elif op in ['PUSH']: # Requires 1 source (reg or literal)
                        if len(args) != 1: raise ValueError(f"{op} requires 1 source argument")
                        op_method(args[0]) # Method handles validation via _get_value
                    elif op in ['POP']: # Requires 1 register destination
                         if len(args) != 1: raise ValueError(f"{op} requires 1 register argument")
                         reg = args[0]
                         if not self.validate_register(reg): raise ValueError(f"Invalid register for {op}: {reg}")
                         op_method(reg.upper())
                    elif op in ['IN']: # Requires 1 register destination
                         if len(args) != 1: raise ValueError(f"{op} requires 1 register argument")
                         reg = args[0]
                         if not self.validate_register(reg): raise ValueError(f"Invalid register for {op}: {reg}")
                         op_method(reg.upper())
                    elif op in ['OUT']: # Requires 1 source (reg or literal)
                        if len(args) != 1: raise ValueError(f"{op} requires 1 source argument")
                        op_method(args[0]) # Method handles validation via _get_value
                    elif op in ['LDA', 'STA']: # Require reg, addr or addr, src
                         if len(args) != 2: raise ValueError(f"{op} requires 2 arguments")
                         arg1, arg2 = args[0], args[1]
                         if op == 'LDA':
                             if not self.validate_register(arg1): raise ValueError(f"Invalid destination register for {op}: {arg1}")
                             op_method(arg1.upper(), arg2) # Address validation happens inside
                         else: # STA
                             op_method(arg1, arg2) # Address validation inside, source validation via _get_value inside
                    elif op in ['CMP', 'MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'OR', 'AND', 'XOR']: # Require 2 args (dest usually reg)
                        if len(args) != 2: raise ValueError(f"{op} requires 2 arguments")
                        arg1, arg2 = args[0], args[1]
                        # Destination register validation needed for non-CMP ops
                        if op != 'CMP':
                            if not self.validate_register(arg1): raise ValueError(f"Invalid destination register for {op}: {arg1}")
                            op_method(arg1.upper(), arg2) # Source validation via _get_value inside method
                        else: # CMP can have Reg, Reg | Reg, Lit | Lit, Reg | Lit, Lit
                            op_method(arg1, arg2) # Validation via _get_value inside method
                    elif op in ['ROR', 'ROL', 'SHL', 'SHR']: # Require Reg, Count (Reg or Lit)
                         if len(args) != 2: raise ValueError(f"{op} requires 2 arguments (register, count)")
                         reg, count_src = args[0], args[1]
                         if not self.validate_register(reg): raise ValueError(f"Invalid register for {op}: {reg}")
                         count_val = self._get_value(count_src) # Resolve count source
                         op_method(reg.upper(), count_val)
                    else:
                         # Should not happen if op is in self.operations, but as fallback:
                         raise NotImplementedError(f"Execution logic missing for operation: {op}")

                    pc += 1 # Increment PC *after* successful non-branching operation

                else: # Operation not found
                    raise ValueError(f"Unknown operation: {op}")

                # Print state after successful execution of the instruction (if verbose)
                if self.verbose:
                    self.print_state()

            except (ValueError, StackOverflowError, StackUnderflowError, IndexError, KeyError, NotImplementedError) as e:
                error_message = f"Error at line {line_num_display} ('{instruction}'): {type(e).__name__} - {str(e)}"
                print(f"\n{error_message}", file=sys.stderr)
                self.flags['Error'] = True
                # Decide whether to halt or try to continue (halting is safer)
                print("--- Execution Aborted Due to Error ---")
                return # Halt execution

            except Exception as e: # Catch unexpected errors
                error_message = f"Unexpected error at line {line_num_display} ('{instruction}'): {type(e).__name__} - {str(e)}"
                print(f"\n{error_message}", file=sys.stderr)
                self.flags['Error'] = True
                print("--- Execution Aborted Due to Unexpected Error ---")
                return # Halt execution


        # End of program reached if loop terminates naturally
        if self.verbose:
             print("\n--- Program Execution End (reached end of code) ---")


    def load_program(self, filename):
        """Load program from file, removing comments and blank lines."""
        program = []
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    cleaned = line.split(';')[0].strip() # Remove comments, strip whitespace
                    if cleaned: # Only add non-empty lines
                        program.append(cleaned)
                except Exception as e:
                    raise IOError(f"Error reading program file '{filename}' at line {line_num}: {e}")
        return program

    def save_memory_dump(self, filename, fmt='hex'):
        """Save memory contents to file (hex or decimal format)."""
        with open(filename, 'w') as f:
            for addr in range(self.memory_size):
                val = self.memory[addr]
                if fmt.lower() == 'hex':
                    # Format address and value as hex (adjust padding as needed)
                    hex_addr_digits = (self.memory_size.bit_length() + 3) // 4
                    hex_val_digits = self.hex_digits
                    line = f"{addr:0{hex_addr_digits}X}: {val:0{hex_val_digits}X}\n"
                else: # Default to decimal
                    line = f"{addr}: {val}\n"
                f.write(line)

    def load_memory_dump(self, filename, fmt='hex'):
        """Load memory contents from file (hex or decimal format)."""
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                cleaned = line.split('#')[0].strip() # Allow '#' comments in dump files
                if not cleaned: continue

                try:
                    addr_part, val_part = cleaned.split(':')
                    if fmt.lower() == 'hex':
                        addr = int(addr_part.strip(), 16)
                        value = int(val_part.strip(), 16)
                    else: # Default to decimal
                        addr = int(addr_part.strip())
                        value = int(val_part.strip())

                    # Validate address range and write to memory (applying modulus)
                    if 0 <= addr < self.memory_size:
                        self.memory[addr] = value % self.modulus
                    else:
                        print(f"Warning: Address {addr} out of range (0-{self.memory_size-1}) on line {line_num} in dump file.", file=sys.stderr)

                except (ValueError, IndexError) as e:
                    print(f"Warning: Skipping invalid line {line_num} in dump file ('{cleaned}'): {e}", file=sys.stderr)
                    continue # Skip invalid lines

    def print_state(self, show_memory=8):
        """Display current state of Registers, Flags, and Memory."""
        print(f"  Registers ({self.bit_size}-bit):")
        for reg, value in self.registers.items():
            bits = self._format_bits(value)
            highlighted = ' '.join(bits) # Add spaces between bits
            print(f"    {reg}: {value:4d} (0x{value:0{self.hex_digits}X} | {highlighted})")

        print("  Status flags:")
        # Sort flags for consistent order? Optional.
        for flag, state in sorted(self.flags.items()):
            print(f"    {flag:<10}: {state}")

        print(f"  Stack Pointer (SP): {self.sp:04X} ({self.sp})")

        if show_memory > 0:
             print(f"  Memory (showing first {show_memory} and stack area):")
             # Show first few locations
             for i in range(min(show_memory, self.memory_size)):
                 val = self.memory[i]
                 bits = self._format_bits(val)
                 highlighted = ' '.join(bits)
                 print(f"    [{i:0{self.hex_digits}X}]: {val:4d} (0x{val:0{self.hex_digits}X} | {highlighted})")

             # Show stack area if different from the start
             stack_preview_start = max(0, self.sp - show_memory // 2)
             stack_preview_end = min(self.memory_size, self.stack_base + 2) # Show up to base + 1

             if stack_preview_start >= min(show_memory, self.memory_size):
                 print("    ...") # Indicate gap if stack area is far from start

             for i in range(stack_preview_start, stack_preview_end):
                 # Avoid re-printing if already shown
                 if i >= min(show_memory, self.memory_size):
                      val = self.memory[i]
                      bits = self._format_bits(val)
                      highlighted = ' '.join(bits)
                      sp_marker = "<= SP" if i == self.sp else ""
                      base_marker = "<= BASE" if i == self.stack_base else ""
                      limit_marker = "<= LIMIT" if i == self.stack_limit else ""
                      io_marker = "<= IO_IN" if i == self.io_input_addr else "<= IO_OUT" if i == self.io_output_addr else ""
                      marker = f"{sp_marker}{base_marker}{limit_marker}{io_marker}"
                      print(f"    [{i:0{self.hex_digits}X}]: {val:4d} (0x{val:0{self.hex_digits}X} | {highlighted}) {marker}")


    # --- CPU Instruction Implementations ---

    # --- Arithmetic Operations ---
    def inc(self, reg):
        """INC: Increment register by 1."""
        original = self.registers[reg]
        result = original + 1
        self.registers[reg] = result % self.modulus
        # Flags
        self.flags['Carry'] = result > self.max_value # Carry on unsigned wrap
        self._update_zero(self.registers[reg])
        original_signed = self._to_signed(original)
        self.flags['Overflow'] = (original_signed == self.max_signed) # Signed overflow on wrap

    def dec(self, reg):
        """DEC: Decrement register by 1."""
        original = self.registers[reg]
        result = original - 1
        self.registers[reg] = result % self.modulus
        # Flags
        self.flags['Carry'] = (original == 0) # Borrow flag (set if original was 0)
        self._update_zero(self.registers[reg])
        original_signed = self._to_signed(original)
        self.flags['Overflow'] = (original_signed == self.min_signed) # Signed overflow on wrap

    def add_op(self, dest, src):
        """ADD: Add source value to destination register."""
        a = self.registers[dest]
        b = self._get_value(src)
        result = a + b
        self.registers[dest] = result % self.modulus
        # Flags
        self.flags['Carry'] = result > self.max_value # Unsigned carry
        self._update_zero(self.registers[dest])
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        sum_signed = a_signed + b_signed
        self.flags['Overflow'] = not (self.min_signed <= sum_signed <= self.max_signed) # Signed overflow

    def sub_op(self, dest, src):
        """SUB: Subtract source value from destination register."""
        a = self.registers[dest]
        b = self._get_value(src)
        result = a - b
        self.registers[dest] = result % self.modulus
        # Flags
        self.flags['Carry'] = a < b  # Borrow flag (set if unsigned borrow needed)
        self._update_zero(self.registers[dest])
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        diff_signed = a_signed - b_signed
        self.flags['Overflow'] = not (self.min_signed <= diff_signed <= self.max_signed) # Signed overflow

    def mul_op(self, dest, src):
        """MUL: Multiply destination register by source value (unsigned)."""
        a = self.registers[dest]
        b = self._get_value(src)
        result = a * b
        self.registers[dest] = result % self.modulus
        # Flags
        # Carry could indicate if upper bits were lost, approximation:
        self.flags['Carry'] = result > self.max_value
        self._update_zero(self.registers[dest])
        # Overflow for signed multiplication (more complex, approx check):
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        product_signed = a_signed * b_signed
        self.flags['Overflow'] = not (self.min_signed <= product_signed <= self.max_signed)

    def div_op(self, dest, src):
        """DIV: Unsigned integer division: dest = dest // src."""
        a = self.registers[dest]
        b = self._get_value(src)
        if b == 0:
            self.flags['Error'] = True
            # Option: raise error OR just set flag and result? Let's raise.
            raise ValueError("Division by zero")
        self.registers[dest] = (a // b) # Integer division result fits in bits by definition
        # Flags
        self._update_zero(self.registers[dest])
        self.flags['Carry'] = False # Typically reset by DIV/MOD
        self.flags['Overflow'] = False # Typically reset by DIV/MOD

    def mod_op(self, dest, src):
        """MOD: Unsigned modulo: dest = dest % src."""
        a = self.registers[dest]
        b = self._get_value(src)
        if b == 0:
            self.flags['Error'] = True
            raise ValueError("Modulo by zero")
        self.registers[dest] = (a % b) # Modulo result fits in bits by definition
        # Flags
        self._update_zero(self.registers[dest])
        self.flags['Carry'] = False # Typically reset by DIV/MOD
        self.flags['Overflow'] = False # Typically reset by DIV/MOD

    # --- Logic Operations ---
    def not_op(self, reg):
        """NOT: Bitwise NOT on register."""
        self.registers[reg] = (~self.registers[reg]) & self.max_value
        # Flags
        self._update_zero(self.registers[reg])
        # Carry/Overflow usually unaffected by NOT

    def or_op(self, dest, src):
        """OR: Bitwise OR: dest = dest | src."""
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] | src_val) & self.max_value
        # Flags
        self._update_zero(self.registers[dest])
        self.flags['Carry'] = False # Usually reset
        self.flags['Overflow'] = False # Usually reset

    def and_op(self, dest, src):
        """AND: Bitwise AND: dest = dest & src."""
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] & src_val) & self.max_value
        # Flags
        self._update_zero(self.registers[dest])
        self.flags['Carry'] = False # Usually reset
        self.flags['Overflow'] = False # Usually reset

    def xor_op(self, dest, src):
        """XOR: Bitwise XOR: dest = dest ^ src."""
        src_val = self._get_value(src)
        self.registers[dest] = (self.registers[dest] ^ src_val) & self.max_value
        # Flags
        self._update_zero(self.registers[dest])
        self.flags['Carry'] = False # Usually reset
        self.flags['Overflow'] = False # Usually reset

    # --- Shift/Rotate Operations ---
    def ror(self, reg, count):
        """ROR: Rotate Right register by count bits."""
        value = self.registers[reg]
        count = count % self.bit_size  # Normalize shift count
        if count == 0: return # No change, no flag updates needed? Or update zero? Let's update zero.

        mask = (1 << count) - 1
        shifted_out = value & mask
        new_value = (value >> count) | (shifted_out << (self.bit_size - count))
        self.registers[reg] = new_value
        # Flags
        carry_bit = (value >> (count - 1)) & 1 # Last bit shifted out
        self.flags['Carry'] = bool(carry_bit)
        self._update_zero(new_value)
        # Overflow flag state after ROR is sometimes defined (e.g., if MSB changes), sometimes not. Let's leave it unchanged.

    def rol(self, reg, count):
        """ROL: Rotate Left register by count bits."""
        value = self.registers[reg]
        count = count % self.bit_size  # Normalize shift count
        if count == 0: return

        shifted_out = (value >> (self.bit_size - count)) # Bits that wrap around
        new_value = ((value << count) | shifted_out) & self.max_value
        self.registers[reg] = new_value
        # Flags
        carry_bit = (value >> (self.bit_size - 1)) & 1 # MSB before rotate becomes carry? Or last bit rotated into carry? Let's use MSB.
        # A common definition: Carry = MSB for ROL 1. For >1, it's the last bit shifted out of MSB pos.
        carry_bit = (value >> (self.bit_size - count)) & 1 # Last bit shifted out of MSB position
        self.flags['Carry'] = bool(carry_bit)
        self._update_zero(new_value)
        # Overflow undefined/unchanged

    def shl(self, reg, count):
        """SHL: Shift Left register by count bits (logical)."""
        value = self.registers[reg]
        count = count % self.bit_size # Normalize shift count (or maybe clamp to bit_size?) Let's use modulo.
        if count == 0: return

        new_value = (value << count) & self.max_value # Apply bit mask after shift
        # Flags
        carry = (value >> (self.bit_size - count)) & 1 # Last bit shifted out of MSB
        self.flags['Carry'] = bool(carry)
        self.registers[reg] = new_value
        self._update_zero(new_value)
        # Overflow: Often set if the sign bit changes during SHL 1. More complex for count > 1. Let's ignore for now.

    def shr(self, reg, count):
        """SHR: Shift Right register by count bits (logical)."""
        value = self.registers[reg]
        count = count % self.bit_size # Normalize
        if count == 0: return

        new_value = value >> count
        # Flags
        carry = (value >> (count - 1)) & 1 # Last bit shifted out of LSB
        self.flags['Carry'] = bool(carry)
        self.registers[reg] = new_value
        self._update_zero(new_value)
        # Overflow usually reset

    # --- Data Movement Operations ---
    def mov(self, dest, src):
        """MOV: Move value from source (reg/literal) to destination register."""
        # _get_value handles resolving source and applying modulus if literal
        value = self._get_value(src)
        self.registers[dest] = value
        # Flags: Typically MOV does not affect flags.

    # --- Memory Access Operations ---
    def lda(self, dest_reg, address_src):
        """LDA: Load value from memory address (or I/O) into register."""
        addr = self._resolve_address(address_src)

        if addr == self.io_input_addr:
            # Memory-mapped I/O Read
            value, _ = self._io_read()
            final_value = value % self.modulus # Ensure value fits register
        else:
            # Normal memory read
            final_value = self.memory[addr]

        self.registers[dest_reg] = final_value
        # Flags: Update Zero flag based on loaded value. Others unaffected.
        self._update_zero(final_value)

    def sta(self, address_dest, src):
        """STA: Store value from source (reg/literal) to memory address (or I/O)."""
        addr = self._resolve_address(address_dest)
        # _get_value handles resolving source and applying modulus if literal
        value = self._get_value(src)

        if addr == self.io_output_addr:
            # Memory-mapped I/O Write
            self._io_write(value)
        else:
            # Normal memory write
            self.memory[addr] = value # Store the resolved value
        # Flags: STA typically does not affect flags.

    # --- Stack Operations ---
    def push(self, src):
        """PUSH: Push value from source (reg/literal) onto the stack."""
        if self.sp == self.stack_limit:
            raise StackOverflowError(f"Stack overflow: SP ({self.sp}) cannot go below stack limit ({self.stack_limit})")

        value = self._get_value(src) # Resolve value first
        self.sp = (self.sp - 1 + self.memory_size) % self.memory_size # Decrement SP (downwards stack) safely
        self.memory[self.sp] = value

        if self.verbose:
            print(f"  Stack: Pushed {value} to address {self.sp:0{self.hex_digits}X}")
        # Flags: PUSH typically does not affect flags.

    def pop(self, dest):
        """POP: Pop value from stack into destination register."""
        # Validation happens in execute before call, but double-check here?
        # if not self.validate_register(dest):
        #     raise ValueError(f"Invalid register for POP: {dest}")

        if self.sp == self.stack_base:
             # Check if stack pointer is at base *before* trying to read/increment
            raise StackUnderflowError("POP failed: Stack is empty (SP at base)")

        value = self.memory[self.sp] # Read value from current SP
        current_sp = self.sp
        self.sp = (self.sp + 1) % self.memory_size # Increment SP (move up after pop)

        self.registers[dest] = value
        if self.verbose:
            print(f"  Stack: Popped {value} from address {current_sp:0{self.hex_digits}X} into {dest}")

        # Flags: Update Zero based on popped value. Others typically unaffected.
        self._update_zero(value)


    # --- I/O Operations ---
    def in_op(self, dest_reg):
        """IN: Read value from dedicated I/O input into register."""
        # Validation happens in execute before call
        value, char_read = self._io_read() # Use helper
        final_value = value % self.modulus
        self.registers[dest_reg] = final_value

        if self.verbose:
            if char_read is not None:
                print(f"  Input: '{char_read}' -> {value}(raw) -> {final_value}({dest_reg})")
            else:
                print(f"  Input: Error -> {value}(raw) -> {final_value}({dest_reg})")
        # Flags: Update Zero based on input value. Others unaffected.
        self._update_zero(final_value)


    def out_op(self, src):
        """OUT: Write value from source (reg/literal) to dedicated I/O output."""
        value = self._get_value(src) # Resolve source
        self._io_write(value) # Use helper (handles verbose internally)
        # Flags: OUT typically does not affect flags.


    # --- Comparison Operation ---
    def cmp_op(self, src1, src2):
        """CMP: Compare src1 and src2, setting flags (result is discarded)."""
        a = self._get_value(src1)
        b = self._get_value(src2)
        result = a - b # Perform subtraction internally

        # Flags: Set based on the subtraction result
        # Zero flag: set if result is 0
        self.flags['Zero'] = (result % self.modulus) == 0
        # Carry flag (borrow): set if unsigned subtraction required borrow
        self.flags['Carry'] = a < b
        # Overflow flag: set if signed subtraction resulted in overflow
        a_signed = self._to_signed(a)
        b_signed = self._to_signed(b)
        diff_signed = a_signed - b_signed
        self.flags['Overflow'] = not (self.min_signed <= diff_signed <= self.max_signed)


    # --- Program Loading & Preprocessing Helpers ---

    def _preprocess_labels(self, program):
        """Two-pass process to find labels and resolve references."""
        labels, pass1_processed = self._collect_labels(program)
        resolved_program = self._resolve_references(pass1_processed, labels)
        return resolved_program

    def _collect_labels(self, program):
        """First pass: identify labels and their program counter locations (0-based)."""
        labels = {}
        processed = []
        current_pc = 0
        for line in program:
            clean_line = self._clean_line(line)
            if not clean_line:
                continue # Skip empty lines after cleaning

            label, instruction = self._extract_label(clean_line)
            if label:
                if label in labels:
                     # Consider raising error or warning for duplicate labels
                     print(f"Warning: Duplicate label '{label}' found. Using first definition at PC {labels[label]}.", file=sys.stderr)
                else:
                    labels[label] = current_pc # Store 0-based PC

            if instruction:
                # Normalize instruction parts (opcodes to upper, etc.) for consistency
                normalized_instr = self._normalize_instruction(instruction)
                processed.append(normalized_instr)
                current_pc += 1 # Increment PC only for lines with instructions

        return labels, processed

    def _resolve_references(self, processed_program, labels):
        """Second pass: replace label references in arguments with their PC values."""
        resolved_program = []
        for instruction in processed_program:
            parts = instruction.replace(',', ' ').split()
            if not parts: continue

            operation = parts[0].upper() # Already upper from normalize, but safe
            resolved_args = []
            for arg in parts[1:]:
                # Pass labels dict to resolve potential label references
                resolved_arg = self._process_argument(arg, labels)
                resolved_args.append(resolved_arg)

            resolved_program.append(' '.join([operation] + resolved_args))
        return resolved_program

    def _clean_line(self, line):
        """Remove comments and normalize whitespace."""
        return line.split(';')[0].strip() # Keep original case for now, normalize later

    def _extract_label(self, line):
        """Separate label (ending with ':') from instruction if present."""
        if ':' in line:
             label_part, _, instr_part = line.partition(':')
             # Validate label format? (e.g., no whitespace)
             return label_part.strip().upper(), instr_part.strip() # Normalize label to upper
        else:
             return None, line.strip() # No label found

    def _normalize_instruction(self, instr):
        """Ensure consistent formatting: Uppercase opcode, keep args as is for now."""
        parts = instr.split(maxsplit=1)
        if not parts: return ""
        op = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        # Further normalization (e.g., spacing around commas) could happen here if needed
        return f"{op} {args}".strip() # Simple space separation


    def _process_argument(self, arg, labels):
        """Resolve individual argument: Label -> PC, Register -> Upper, Literal -> Normalized."""
        upper_arg = arg.upper() # Check labels/registers case-insensitively
        if upper_arg in labels:
            return str(labels[upper_arg]) # Replace label with its PC value (as string)
        elif self.validate_register(upper_arg):
            return upper_arg # Return validated, uppercase register name
        else:
            # Assume it's a literal, normalize it
            return self._normalize_literal(arg)

    def _normalize_literal(self, value):
        """Standardize numeric literals (e.g., lowercase hex/bin prefixes)."""
        # Check if it's potentially a number before lowercasing etc.
        # This prevents errors if an invalid non-numeric arg reaches here.
        try:
            # Attempt a basic check using _get_value logic without storing
            self._is_valid_literal(value)
            # If valid, normalize case for prefixes
            val_lower = value.lower()
            if val_lower.startswith('0x') or val_lower.startswith('0b'):
                return val_lower
            return value # Return original decimal or potentially other valid formats
        except ValueError:
             # If it's not a valid literal according to our rules, return as is.
             # Error should be caught later during _get_value if used inappropriately.
             return value
        except AttributeError: # Handle non-string inputs if they somehow occur
             return value


    # --- Internal I/O Helpers ---

    def _io_read(self):
        """Reads a single character from standard input, returns (ord_value, char)."""
        try:
            print("\nInput > ", end='', flush=True) # Prompt on same line
            char = sys.stdin.read(1) # Read exactly one character
            if not char: # Handle EOF or empty input stream
                 print("\nInput Error: End of input detected. Using default value 0.", flush=True)
                 return 0, None
            value = ord(char)
            # Consume trailing newline if present (common in interactive input)
            if char == '\n': # If user just pressed Enter, read might return '\n'
                print("\nInput Error: Newline received. Using default value 0.", flush=True)
                return 0, None # Treat Enter as invalid input for single char
            # Optional: consume rest of line if user types more than one char?
            # sys.stdin.readline() # Uncomment to clear buffer after one char
            return value, char
        except Exception as e: # Catch potential ord() errors or other issues
            print(f"\nInput Error ({type(e).__name__}). Using default value 0.", flush=True)
            return 0, None

    def _io_write(self, value):
        """Writes a character corresponding to the value to standard output."""
        try:
            # Ensure value is within valid range for output? Modulo might handle this.
            safe_value = value % 256 # Limit to typical byte range for chr() safety
            char_to_print = chr(safe_value)
            output_target = sys.stdout # Or could be configurable
        except ValueError:
            # Value out of range for chr (less likely with modulo)
            char_to_print = '?' # Placeholder for unprintable value
            if self.verbose:
                print(f"\nOutput Warning: Value {value} resulted in unprintable char. Printing '?'.", end='', flush=True)

        if self.verbose:
             # Create printable representation, handle non-ASCII/control chars
            printable_char = char_to_print if 32 <= safe_value <= 126 else f'\\x{safe_value:02X}'
            print(f"\n  Output: {value} -> '{printable_char}'", end='', flush=True)
        else:
            # Write directly to standard output
            print(char_to_print, end='', file=output_target, flush=True)


    # --- Internal Value/Validation/Flag Helpers ---

    def _get_value(self, src):
        """Resolve source operand (register or literal) to its integer value."""
        upper_src = str(src).upper() # Work with uppercase for register check
        if self.validate_register(upper_src):
            return self.registers[upper_src]

        # If not a register, try parsing as a literal
        try:
            src_str = str(src) # Ensure it's a string for parsing
            src_lower = src_str.lower()
            base = 10
            if src_lower.startswith('0x'):
                base = 16
                src_clean = src_lower[2:]
            elif src_lower.startswith('0b'):
                base = 2
                src_clean = src_lower[2:]
            else:
                # Ensure it's not empty or just a sign after cleaning prefixes
                src_clean = src_lower
                if not src_clean or src_clean in ['+', '-']: raise ValueError("Empty number")

            value = int(src_clean, base)
            # Return value constrained by the VM's bit size
            return value % self.modulus
        except (ValueError, TypeError):
            raise ValueError(f"Invalid source operand: '{src}' is not a valid register or literal number.")


    def _is_valid_literal(self, value):
        """Check if a string represents a valid numeric literal for this VM."""
        try:
            # Use the core logic of _get_value without storing the result
            val_str = str(value)
            val_lower = val_str.lower()
            base = 10
            if val_lower.startswith('0x'): base = 16; src_clean = val_lower[2:]
            elif val_lower.startswith('0b'): base = 2; src_clean = val_lower[2:]
            else: src_clean = val_lower;
            if not src_clean or src_clean in ['+', '-']: return False # Check empty after prefix removal
            int(src_clean, base) # Attempt conversion
            return True
        except (ValueError, TypeError):
            return False


    def validate_register(self, reg):
        """Check if string is a valid register name (case-insensitive)."""
        return isinstance(reg, str) and reg.upper() in self.registers


    def _resolve_address(self, address_src):
        """Convert address source (reg/literal) to a valid memory index."""
        address = self._get_value(address_src) # Gets value, applies modulus based on bit size
        # Ensure address is within memory bounds (modulo might not be enough if addr > mem_size)
        final_addr = address % self.memory_size
        return final_addr


    def _to_signed(self, value):
        """Convert stored unsigned value to its signed interpretation."""
        # Assumes 2's complement
        if value & (1 << (self.bit_size - 1)): # Check sign bit
            # Negative number
            return value - self.modulus
        else:
            # Positive number
            return value


    def _update_zero(self, value):
        """Update Zero flag based on value being 0."""
        # Ensure value is compared after fitting into the modulus
        self.flags['Zero'] = (value % self.modulus == 0)


    def _format_bits(self, value):
        """Format integer value as a binary string with proper bit length."""
        return format(value % self.modulus, f'0{self.bit_size}b')

# --- Example Usage (Remains outside the class) ---
if __name__ == "__main__":
    print("--- VM Demo ---")
    # Example: Create a VM instance (adjust parameters as needed)
    # Increase memory size for stack testing
    cpu = VirtualMachine(bit_size=8, memory_size=32, verbose=True)

    # Simple program demonstrating various features
    program = [
        "; Label/Jump/Compare Demo",
        "START: ",
        "  MOV R0, 0x10  ; Load initial value",
        "LOOP: ",
        "  PRINT_R0: OUT R0 ; Output current R0 value (as character)",
        "  INC R0        ; Increment R0",
        "  CMP R0, 0x15  ; Compare R0 with limit",
        "  JNZ LOOP      ; Jump back to LOOP if not zero (R0 != 0x15)",
        "  MOV R1, MSG_DONE ; Load address of message into R1",
        "PRINT_LOOP:",
        "  LDA R2, R1    ; Load character from address in R1 into R2",
        "  CMP R2, 0     ; Check for null terminator",
        "  JZ END_PROG   ; If zero, jump to end",
        "  OUT R2        ; Output character",
        "  INC R1        ; Increment memory address pointer",
        "  JMP PRINT_LOOP ; Loop back",
        "END_PROG:",
        "  HLT           ; Halt execution",
        "",
        "; Data section (using memory loading)",
        "MSG_DONE:" # This label's address needs to be calculated/placed correctly
                    # Manual placement for demo: Assuming this program uses ~15 instructions,
                    # place data far enough away, e.g., at memory location 20 (0x14).
                    # Note: This requires loading data separately or a more advanced assembler.
    ]

    # Load data into memory manually for the demo
    msg_addr = 20 # 0x14
    done_msg = " Done!\n\0" # Null-terminated string
    for i, char in enumerate(done_msg):
        if msg_addr + i < cpu.memory_size:
            cpu.memory[msg_addr + i] = ord(char)
        else:
            print("Warning: Not enough memory to load full message.")
            break

    # Manually insert the message address into the MOV instruction after label preprocessing
    # This is a HACK because label preprocessing currently only resolves jump targets.
    # A proper assembler would handle data labels.
    def insert_data_address(prog_lines, label_name, address, target_instruction_index):
         # Find the instruction and replace the placeholder label with the address
         instr = prog_lines[target_instruction_index]
         parts = instr.split()
         # Assuming format "MOV R1, MSG_DONE" -> "MOV R1, <address>"
         if len(parts) == 3 and parts[0] == "MOV" and parts[2] == label_name:
              prog_lines[target_instruction_index] = f"{parts[0]} {parts[1]}, {address}"
         else:
              print(f"Warning: Could not find instruction to patch for label {label_name}")

    # Preprocess first to know instruction count/indices
    temp_processed = cpu._preprocess_labels(program)

    # Find the index of "MOV R1, MSG_DONE" - Adjust index if program changes!
    # This is fragile and demonstrates the need for a better assembler.
    try:
        mov_instr_index = -1
        for idx, line in enumerate(temp_processed):
            if line.startswith("MOV R1, MSG_DONE"):
                 mov_instr_index = idx
                 break
        if mov_instr_index != -1:
             insert_data_address(temp_processed, "MSG_DONE", msg_addr, mov_instr_index)
             print(f"\nPatched instruction at index {mov_instr_index}: {temp_processed[mov_instr_index]}")
        else:
             print("Warning: Could not find MOV instruction to patch.")
    except Exception as e:
         print(f"Error during patching: {e}")


    print("\n--- Final Preprocessed Program ---")
    for idx, line in enumerate(temp_processed):
        print(f"{idx:2d}: {line}")

    print("\n--- Starting Execution ---")
    try:
        cpu.execute(temp_processed) # Execute the (potentially patched) processed program
    except Exception as e:
        print(f"\n--- Execution Failed: {type(e).__name__} - {e} ---", file=sys.stderr)
        cpu.print_state() # Print state on failure

    print("\n--- Final VM State ---")
    cpu.print_state(show_memory=cpu.memory_size) # Show all memory

    # Example of saving memory dump
    # cpu.save_memory_dump("memory_dump.txt", fmt='hex')