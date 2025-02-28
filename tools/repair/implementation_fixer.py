#!/usr/bin/env python3
"""
Implementation Fixer - Automatically fixes common implementation issues in UE code
"""

import os
import re
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('implementation_fixer')


class ImplementationFixer:
    """Fixes common implementation issues in Unreal Engine code"""
    
    def _discover_project_structure(self):
       """Dynamically discover the project structure"""
       structure = {
           'modules': {}
       }
       
       # Find all module directories
       for item in self.source_dir.iterdir():
           if item.is_dir():
               public_dir = item / "Public"
               private_dir = item / "Private"
               
               if public_dir.exists() and private_dir.exists():
                   structure['modules'][item.name] = {
                       'path': item,
                       'public': public_dir,
                       'private': private_dir
                   }
       
       logger.info(f"Discovered {len(structure['modules'])} modules: {', '.join(structure['modules'].keys())}")
       return structure

    def discover_implementation_patterns(self):
        """Dynamically discover implementation patterns in any UE plugin"""
        patterns = {
            'interfaces': [],
            'delegates': [],
            'rpcs': [],
            'blueprintEvents': [],
            'replicationProperties': []
        }
        
        # Scan all header files for interface definitions
        for header_file in self.source_dir.glob("**/*.h"):
            with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Find interface declarations (both UINTERFACE and direct I-prefixed classes)
                uinterface_matches = re.finditer(r'UINTERFACE\s*\([^\)]*\)\s*\n\s*class\s+[A-Z_]+_API\s+U(\w+)\s*:\s*public\s+UInterface', content)
                for match in uinterface_matches:
                    interface_name = 'I' + match.group(1).lstrip('U')
                    
                    # Find the actual interface class
                    interface_class_match = re.search(r'class\s+[A-Z_]+_API\s+' + interface_name + r'\s*[^{]*{([^}]*)}', content, re.DOTALL)
                    if interface_class_match:
                        interface_body = interface_class_match.group(1)
                        
                        # Extract required methods
                        method_matches = re.finditer(r'virtual\s+([^\(;]+)\s+([A-Za-z0-9_]+)\s*\(([^\)]*)\)[^;]*;\s*(?://[^\n]*)?', interface_body)
                        methods = []
                        
                        for m_match in method_matches:
                            return_type = m_match.group(1).strip()
                            method_name = m_match.group(2).strip()
                            params = m_match.group(3).strip()
                            
                            methods.append({
                                'name': method_name,
                                'return_type': return_type,
                                'params': params,
                                'signature': f"{return_type} {method_name}({params})"
                            })
                        
                        patterns['interfaces'].append({
                            'name': interface_name,
                            'file': str(header_file),
                            'methods': methods
                        })
        
        # Discover RPC patterns (Server, Client, NetMulticast)
        for header_file in self.source_dir.glob("**/*.h"):
            with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Find RPC declarations
                rpc_matches = re.finditer(r'UFUNCTION\s*\(\s*(?:[^\)]*,)?\s*(Server|Client|NetMulticast)\s*(?:[^\)]*)\)\s*\n\s*([^\(]+)\s+([A-Za-z0-9_]+)\s*\(([^\)]*)\)', content)
                
                for match in rpc_matches:
                    rpc_type = match.group(1)
                    return_type = match.group(2).strip()
                    method_name = match.group(3).strip()
                    params = match.group(4).strip()
                    
                    patterns['rpcs'].append({
                        'type': rpc_type,
                        'name': method_name,
                        'return_type': return_type,
                        'params': params,
                        'file': str(header_file)
                    })
        
                # Discover BlueprintNativeEvent patterns
        for header_file in self.source_dir.glob("**/*.h"):
            with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Find BlueprintNativeEvent declarations
                blueprint_matches = re.finditer(r'UFUNCTION\s*\(\s*(?:[^\)]*,)?\s*BlueprintNativeEvent\s*(?:[^\)]*)\)\s*\n\s*([^\(]+)\s+([A-Za-z0-9_]+)\s*\(([^\)]*)\)', content)
                
                for match in blueprint_matches:
                    return_type = match.group(1).strip()
                    method_name = match.group(2).strip()
                    params = match.group(3).strip()
                    
                    patterns['blueprintEvents'].append({
                        'name': method_name,
                        'return_type': return_type,
                        'params': params,
                        'file': str(header_file)
                    })
        
        # Discover replicated properties
        for header_file in self.source_dir.glob("**/*.h"):
            with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Find replicated properties
                replicated_matches = re.finditer(r'UPROPERTY\s*\(\s*(?:[^\)]*,)?\s*(Replicated|ReplicatedUsing\s*=\s*([A-Za-z0-9_]+))\s*(?:[^\)]*)\)\s*\n\s*([^\n;]+)\s+([A-Za-z0-9_]+)\s*;', content)
                
                for match in replicated_matches:
                    replication_type = match.group(1)
                    handler = match.group(2) if match.group(2) else None
                    property_type = match.group(3).strip()
                    property_name = match.group(4).strip()
                    
                    patterns['replicationProperties'].append({
                        'name': property_name,
                        'type': property_type,
                        'replication': replication_type,
                        'handler': handler,
                        'file': str(header_file)
                    })
        
        # Log discovery results
        for pattern_type, items in patterns.items():
            if items:
                logger.info(f"Discovered {len(items)} {pattern_type}: {', '.join([item.get('name', 'unnamed') for item in items[:5]])}{' and more' if len(items) > 5 else ''}")
            else:
                logger.info(f"No {pattern_type} discovered")
        
        # Similarly discover other patterns...
        
        return patterns

    def __init__(self, project_dir):
        """Initialize with project directory"""
        self.project_dir = Path(project_dir)
        self.source_dir = self.project_dir / "Source"
        self.fixes_applied = 0
        self.files_modified = 0
        self.project_structure = self._discover_project_structure()
        self.implementation_patterns = self.discover_implementation_patterns()

    def find_implementation_issues(self):
        """Find common implementation issues using discovery patterns"""
        issues = []
        
        # Scan all CPP files
        for cpp_file in self.source_dir.glob("**/*.cpp"):
            file_issues = self._analyze_cpp_file(cpp_file)
            if file_issues:
                issues.extend(file_issues)
        
        # Log summary of issues found
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
    
        for issue_type, count in issue_types.items():
            logger.info(f"Found {count} {issue_type} issues")

        return issues
    
    def _check_interface_implementations(self, content, file_path):
        """Check for missing interface method implementations"""
        missing_impls = []
        logger.info(f"Checking for interface implementations in {file_path}")
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return missing_impls
            
        class_name = class_name_match.group(1)
        
        # Find corresponding header file
        header_path = self._find_header_for_cpp(file_path)
        if not header_path:
            logger.warning(f"Could not find header file for {file_path}")
            return missing_impls
        
        # Extract implemented interfaces
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            header_content = f.read()
            
            # Find interfaces that the class implements
            interface_matches = re.finditer(r'public\s+(I[A-Z]\w+)', header_content)
            logger.info(f"Found interfaces implemented by {class_name}: {[m.group(1) for m in interface_matches]}")
            for match in interface_matches:
                interface_name = match.group(1)
                logger.info(f"Found interface {interface_name} implemented by {class_name}")
                
                # Find the interface header
                interface_header = self._find_interface_header(interface_name)
                if not interface_header:
                    logger.warning(f"Could not find header for interface {interface_name}")
                    continue
                    
                # Extract required methods from interface
                interface_methods = self._extract_interface_methods(interface_header, interface_name)
                
                # Check if each interface method is implemented
                for method in interface_methods:
                    method_signature = method['signature']
                    method_name = method['name']
                    
                    # Check if implementation exists in the cpp file
                    if not re.search(r'\b' + class_name + r'::\s*' + method_name + r'\s*\(', content):
                        missing_impls.append({
                            'type': 'interface_method',
                            'interface': interface_name,
                            'method_name': method_name,
                            'signature': method_signature,
                            'return_type': method['return_type'],
                            'params': method['params']
                        })
        
        return missing_impls

    def _check_rpc_implementations(self,content, file_path):
            """Check for missing RPC Implementation methods"""
            missing_impls = []

            # Extract Class Name
            class_name_match = re.search(r'(\w+)::\w+\(', content)
            if not class_name_match:
                    return missing_impls
                    
            class_name = class_name_match.group(1)
            
            # Use discovered RPC patterns
            for rpc in self.implementation_patterns.get('rpcs', []):
                rpc_type = rpc['type']
                method_name = rpc['name']
                
                #check if this RPC is for this class (comparing header file paths)
                header_path = self._find_header_for_cpp(file_path)
                if not header_path or str(header_path) != rpc['file']:
                    continue
                
                #For Server RPCs, check for _Implementation suffix
                if rpc_type == 'Server':
                    impl_name = f"{method_name}_Implementation"
                    if not re.search(r'\b' + class_name + r'::\s*' + impl_name + r'\s*\(', content):
                        missing_impls.append({
                            'type': 'rpc_implementation',
                            'rpc_type': rpc_type,
                            'method_name': method_name,
                            'impl_name': impl_name,
                            'return_type': rpc['return_type'],
                            'params': rpc['params']
                        })
                        
                # For Client/NetMulticast RPCs, check for regular implementation
                else:
                    if not re.search(r'\b' + class_name + r'::\s*' + method_name + r'\s*\(', content):
                        missing_impls.append({
                            'type': 'rpc_implementation',
                            'rpc_type': rpc_type,
                            'method_name': method_name,
                            'impl_name': impl_name,
                            'return_type': rpc['return_type'],
                            'params': rpc['params']
                        })
            return missing_impls

    def _find_interface_header(self, interface_name):
        """Find the header file for an interface"""
        logger.info(f"Looking for interface header for {interface_name}")
        for module_dir in self.source_dir.glob("**/Public"):
            for header in module_dir.glob("**/*.h"):
                with open(header, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(r'class\s+[A-Z_]+_API\s+' + interface_name + r'\s*:\s*public', content):
                        return header
        return None

    def _extract_interface_methods(self, interface_header, interface_name):
        """Extract required methods from an interface header"""
        methods = []
        
        with open(interface_header, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Find the interface class block
            interface_block_match = re.search(r'class\s+[A-Z_]+_API\s+' + interface_name + r'[^{]*{([^}]*)}', content, re.DOTALL)
            if not interface_block_match:
                return methods
                
            interface_block = interface_block_match.group(1)
            
            # Extract virtual methods (excluding UFUNCTION declarations)
            method_matches = re.finditer(r'virtual\s+([^\(;]+)\s+([A-Za-z0-9_]+)\s*\(([^\)]*)\)[^;]*;', interface_block)
            
            for match in method_matches:
                return_type = match.group(1).strip()
                method_name = match.group(2).strip()
                params = match.group(3).strip()
                
                methods.append({
                    'name': method_name,
                    'return_type': return_type,
                    'params': params,
                    'signature': f"{return_type} {method_name}({params})"
                })
        
        return methods

    def _find_header_for_cpp(self, cpp_file):
        """Find the corresponding header file for a cpp file with improved robustness"""
        # Direct .h equivalent
        direct_header = cpp_file.with_suffix('.h')
        if direct_header.exists():
            return direct_header
            
        # Try to find in Public directory
        file_name = cpp_file.name.replace('.cpp', '.h')
        
        # Get module name from path if possible
        module_name = None
        for module, info in self.project_structure.get('modules', {}).items():
            if str(cpp_file).startswith(str(info['private'])):
                module_name = module
                break
        
        if module_name:
            # Check in module's Public directory
            public_header = self.source_dir / module_name / "Public" / file_name
            if public_header.exists():
                return public_header
                
            # Check in subdirectories of Public
            for potential_header in (self.source_dir / module_name / "Public").glob(f"**/{file_name}"):
                return potential_header
        
        # Fallback: search all Public directories
        for public_dir in self.source_dir.glob("**/Public"):
            for potential_header in public_dir.glob(f"**/{file_name}"):
                return potential_header
                
        return None        

    def _analyze_cpp_file(self, cpp_file):
        """Analyze a CPP file for implementation issues"""
        file_issues = []
        
        with open(cpp_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check for missing includes
            missing_includes = self._check_missing_includes(content, cpp_file)
            if missing_includes:
                file_issues.append({
                    'file': cpp_file,
                    'type': 'missing_includes',
                    'details': missing_includes
                })
            
            # Check for undeclared identifiers
            undeclared = self._check_undeclared_identifiers(content, cpp_file)
            if undeclared:
                file_issues.append({
                    'file': cpp_file,
                    'type': 'undeclared_identifiers',
                    'details': undeclared
                })
            
            # Check for missing implementation methods
            missing_impls = self._check_missing_implementations(content, cpp_file)
            if missing_impls:
                file_issues.append({
                    'file': cpp_file,
                    'type': 'missing_implementations',
                    'details': missing_impls
                })
                
            # NEW: Check for missing interface implementations using discovery patterns
            missing_interface_impls = self._check_interface_implementations(content, cpp_file)
            if missing_interface_impls:
                file_issues.append({
                    'file': cpp_file,
                    'type': 'missing_interface_implementations',
                    'details': missing_interface_impls
                })

            # Check for missing RPC implementations using discovered patterns
            missing_rpc_impls = self._check_rpc_implementations(content, cpp_file)
            if missing_rpc_impls:
                file_issues.append({
                    'file': cpp_file,
                    'type': 'missing_rpc_implementations',
                    'details': missing_rpc_impls
            })
        
        return file_issues    
    
    def _check_missing_includes(self, content, file_path):
        """Check for missing includes based on usage"""
        missing_includes = []
        
        # Common UE types that might need includes
        ue_types = {
            'FString': 'Containers/UnrealString.h',
            'TArray': 'Containers/Array.h',
            'TMap': 'Containers/Map.h',
            'TSet': 'Containers/Set.h',
            'FName': 'UObject/NameTypes.h',
            'FText': 'Internationalization/Text.h',
            'IOnlineSession': 'Online/OnlineSessionInterface.h',
            'FOnlineSessionSearchResult': 'Online/OnlineSessionInterface.h'
        }
        
        # Check if type is used but not included
        for type_name, include_file in ue_types.items():
            if re.search(r'\b' + type_name + r'\b', content) and not re.search(r'#include\s+[<"].*' + include_file + r'[>"]', content):
                missing_includes.append({
                    'type': type_name,
                    'include': include_file
                })
        
        return missing_includes
    
    def _check_undeclared_identifiers(self, content, file_path):
        """Check for likely undeclared identifiers"""
        undeclared = []
        
        # Extract class name to filter out class members
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        class_name = class_name_match.group(1) if class_name_match else None
        
        # Look for error patterns
        error_patterns = [
            r"'(\w+)': undeclared identifier",
            r"'(\w+)': is not a member of '(\w+)'"
        ]
        
        for line in content.split('\n'):
            for pattern in error_patterns:
                match = re.search(pattern, line)
                if match:
                    identifier = match.group(1)
                    undeclared.append({
                        'identifier': identifier,
                        'line': line.strip()
                    })
        
        return undeclared
    
    def _check_missing_implementations(self, content, file_path):
        """Check for methods that need implementation"""
        missing_impls = []
    
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return missing_impls
        
        class_name = class_name_match.group(1)
    
        # Find corresponding header file with more robust path handling
        header_path = None
    
        # Get module name from path
        module_parts = file_path.parts
        module_index = -1
        for i, part in enumerate(module_parts):
            if part == "Source":
                module_index = i + 1
                break
    
        if module_index >= 0 and module_index < len(module_parts):
            module_name = module_parts[module_index]
        
            # Try different potential header locations
            potential_headers = [
                file_path.with_suffix('.h'),  # Same location but .h extension
                self.source_dir / module_name / "Public" / file_path.name.replace('.cpp', '.h'),  # Public dir with same name
                self.source_dir / module_name / "Public" / Path(*file_path.parts[module_index+2:]).with_suffix('.h')  # Relative path in Public
            ]
        
            for potential_header in potential_headers:
                if potential_header.exists():
                    header_path = potential_header
                    break
    
        if not header_path:
            logger.warning(f"Could not find header file for {file_path}")
            return missing_impls
    
        # Extract methods from header
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            header_content = f.read()
        
            # Find BlueprintNativeEvent methods
            for match in re.finditer(r'UFUNCTION\s*\(\s*BlueprintNativeEvent[^\)]*\)\s*\n\s*(\w+)\s+(\w+)\s*\(([^\)]*)\)', header_content):
                return_type, method_name, params = match.groups()
                impl_name = f"{method_name}_Implementation"
            
                # Check if implementation exists
                if not re.search(return_type + r'\s+' + class_name + r'::' + impl_name, content):
                    missing_impls.append({
                        'return_type': return_type,
                        'method_name': method_name,
                        'impl_name': impl_name,
                        'params': params
                    })
    
        return missing_impls

    def _fix_missing_interface_implementations(self, content, missing_impls, file_path):
        """Add missing interface method implementations"""
        if not missing_impls:
            return content
            
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return content
            
        class_name = class_name_match.group(1)
        
        # Find the position to insert implementations (at the end of the file)
        insert_point = len(content)
        
        # Add each missing implementation
        implementations = "\n\n// Auto-generated interface implementations\n"
        for impl_info in missing_impls:
            return_type = impl_info['return_type']
            method_name = impl_info['method_name']
            params = impl_info['params']
            interface = impl_info['interface']
            
            implementation = f"\n{return_type} {class_name}::{method_name}({params})\n{{\n    // TODO: Implement {interface}::{method_name}\n}}\n"
            implementations += implementation
            logger.info(f"Added implementation for interface method: {method_name}")
        
        # Add implementations to the end of the file
        modified_content = content + implementations
        
        return modified_content

    def _fix_missing_rpc_implementations(self, content, missing_impls, file_path):
        """Add missing RPC method implementations with intelligent code generation"""
        if not missing_impls:
            return content
            
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return content
            
        class_name = class_name_match.group(1)
        
        # Find the position to insert implementations (at the end of the file)
        insert_point = len(content)
        
        # Add each missing implementation
        implementations = "\n\n// Auto-generated RPC implementations\n"
        for impl_info in missing_impls:
            return_type = impl_info['return_type']
            method_name = impl_info['method_name']
            impl_name = impl_info['impl_name']
            rpc_type = impl_info['rpc_type']
            params = impl_info['params']
            
            implementation = f"\n{return_type} {class_name}::{impl_name}({params})\n{{\n"
            
            # Generate intelligent implementation based on RPC type
            if rpc_type == 'Server':
                implementation += f"    // TODO: Implement server-side logic for {method_name}\n"
                # Add authority check for server RPCs
                implementation += "    if (!HasAuthority())\n    {\n        return"
                if return_type != "void":
                    if "bool" in return_type.lower():
                        implementation += " false"
                    elif any(num_type in return_type.lower() for num_type in ["int", "float", "double"]):
                        implementation += " 0"
                    else:
                        implementation += " nullptr"
                implementation += ";\n    }\n\n"
            elif rpc_type == 'Client':
                implementation += f"    // TODO: Implement client-side visual/audio effects for {method_name}\n"
            elif rpc_type == 'NetMulticast':
                implementation += f"    // TODO: Implement multicast logic visible to all clients for {method_name}\n"
            
            # Add appropriate return statement based on return type
            if return_type != "void":
                if "bool" in return_type.lower():
                    implementation += "    return false;\n"
                elif "int" in return_type.lower():
                    implementation += "    return 0;\n"
                elif "float" in return_type.lower() or "double" in return_type.lower():
                    implementation += "    return 0.0f;\n"
                elif "FVector" in return_type:
                    implementation += "    return FVector::ZeroVector;\n"
                elif "FRotator" in return_type:
                    implementation += "    return FRotator::ZeroRotator;\n"
                elif "FTransform" in return_type:
                    implementation += "    return FTransform::Identity;\n"
                elif "FString" in return_type:
                    implementation += "    return FString();\n"
                elif "FName" in return_type:
                    implementation += "    return FName();\n"
                elif "FText" in return_type:
                    implementation += "    return FText::GetEmpty();\n"
                else:
                    implementation += "    return nullptr;\n"
            
            implementation += "}\n"
            implementations += implementation
            logger.info(f"Added implementation for {rpc_type} RPC: {impl_name}")
        
        # Add implementations to the end of the file
        modified_content = content + implementations
        
        return modified_content

    def fix_issues(self, issues=None):
        """Fix identified implementation issues"""
        if issues is None:
            issues = self.find_implementation_issues()
        
        for issue in issues:
            file_path = issue['file']
            issue_type = issue['type']
            
            logger.info(f"Fixing {issue_type} in {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            modified_content = content
            
            if issue_type == 'missing_includes':
                modified_content = self._fix_missing_includes(modified_content, issue['details'])
            elif issue_type == 'undeclared_identifiers':
                modified_content = self._fix_undeclared_identifiers(modified_content, issue['details'], file_path)
            elif issue_type == 'missing_implementations':
                modified_content = self._fix_missing_implementations(modified_content, issue['details'], file_path)
            elif issue_type == 'missing_interface_implementations':  
                modified_content = self._fix_missing_interface_implementations(modified_content, issue['details'], file_path)
            elif issue_type == 'missing_rpc_implementations': #newest
                modified_content = self._fix_missing_rpc_implementations(modified_content, issue['details'], file_path)

            if modified_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                self.files_modified += 1
                self.fixes_applied += len(issue['details'])
                logger.info(f"Applied {len(issue['details'])} fixes to {file_path}")
        
        logger.info(f"Total: Applied {self.fixes_applied} fixes across {self.files_modified} files")
        return self.fixes_applied
    
    def _fix_missing_includes(self, content, missing_includes):
        """Add missing includes to the file"""
        if not missing_includes:
            return content
            
        # Find the last include in the file
        last_include_match = re.search(r'(#include\s+[<"][^>"]+[>"]\s*\n)\s*(?!#include)', content)
        if last_include_match:
            insert_point = last_include_match.end(1)
            
            # Add each missing include
            for include_info in missing_includes:
                include_line = f'#include "{include_info["include"]}"\n'
                content = content[:insert_point] + include_line + content[insert_point:]
                insert_point += len(include_line)
                logger.info(f"Added include: {include_info['include']}")
        else:
            # No includes found, add at the top after any comments
            first_non_comment = re.search(r'(^|\n)(?![ \t]*\/)', content)
            if first_non_comment:
                insert_point = first_non_comment.start()
                
                includes_block = ""
                for include_info in missing_includes:
                    includes_block += f'#include "{include_info["include"]}"\n'
                
                content = content[:insert_point] + includes_block + "\n" + content[insert_point:]
                logger.info(f"Added {len(missing_includes)} includes at the top of the file")
        
        return content
    
    def _fix_undeclared_identifiers(self, content, undeclared, file_path):
        """Fix undeclared identifiers"""
        if not undeclared:
            return content
            
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return content
            
        class_name = class_name_match.group(1)
        
        # Find header file
        header_path = None
        for potential_header in [
            file_path.with_suffix('.h'),
            self.source_dir / "Public" / file_path.relative_to(self.source_dir / "Private").with_suffix('.h'),
            self.source_dir / file_path.parent.name / "Public" / file_path.stem.with_suffix('.h')
        ]:
            if potential_header.exists():
                header_path = potential_header
                break
        
        if not header_path:
            logger.warning(f"Could not find header file for {file_path}")
            return content
        
        # Read header content
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            header_content = f.read()
        
        # Add missing member declarations to header
        modified_header = header_content
        
        # Find class declaration in header
        class_decl_match = re.search(r'class\s+[A-Z_]+_API\s+U' + class_name + r'\s*:\s*public\s+(\w+)\s*\{', header_content)
        if not class_decl_match:
            logger.warning(f"Could not find class declaration in {header_path}")
            return content
        
        # Find the position to insert new member declarations
        last_brace_match = re.search(r'};', modified_header)
        if not last_brace_match:
            logger.warning(f"Could not find closing brace in {header_path}")
            return content
            
        insert_point = last_brace_match.start()
        
        # Add members
        added_members = []
        for identifier_info in undeclared:
            identifier = identifier_info['identifier']
            
            # Skip if already declared
            if re.search(r'\b' + identifier + r'\b', header_content):
                continue
                
            # Determine likely type
            var_type = "bool" if identifier.startswith('b') else "int32"
            
            # Add declaration
            member_decl = f"\n    UPROPERTY()\n    {var_type} {identifier};\n"
            modified_header = modified_header[:insert_point] + member_decl + modified_header[insert_point:]
            insert_point += len(member_decl)
            added_members.append(identifier)
            logger.info(f"Added member declaration for: {identifier}")
        
        # Write modified header if changes were made
        if added_members:
            with open(header_path, 'w', encoding='utf-8') as f:
                f.write(modified_header)
            logger.info(f"Updated header {header_path} with {len(added_members)} new member declarations")
        
        return content
    
    def _fix_missing_implementations(self, content, missing_impls, file_path):
        """Add missing method implementations"""
        if not missing_impls:
            return content
            
        # Extract class name
        class_name_match = re.search(r'(\w+)::\w+\(', content)
        if not class_name_match:
            return content
            
        class_name = class_name_match.group(1)
        
        # Find the position to insert implementations (at the end of the file)
        insert_point = len(content)
        
        # Add each missing implementation
        implementations = "\n\n// Auto-generated implementations\n"
        for impl_info in missing_impls:
            return_type = impl_info['return_type']
            method_name = impl_info['method_name']
            impl_name = impl_info['impl_name']
            rpc_type = impl_info['rpc_type']
            params = impl_info['params']
            
            implementation = f"\n{return_type} {class_name}::{impl_name}({params})\n{{\n    // TODO: Implement {method_name}\n}}\n"
            implementations += implementation
            logger.info(f"Added implementation for: {impl_name}")
        
        # Add appropriate return statement based on return type
        if return_type != "void":
            if return_type in ["bool", "BOOL"]:
                implementation += "    return false;\n"
            elif return_type in ["int32", "uint32"]:
                implementation += "    return 0;\n"
            elif "FVector" in return_type:
                implementation += "    return FVector::ZeroVector;\n"
            elif "FRotator" in return_type:
                implementation += "    return FRotator::ZeroRotator;\n"
            else:
                implementation += "    return nullptr;\n"

        implementation += "]\n"
        implementations += implementation
        logger.info(f"Added Implementation for {rpc_type} RPC: {impl_name}")


        # Add implementations to the end of the file
        modified_content = content + implementations
        
        return modified_content
    
    def fix_netforge_types(self):
        """Create missing NetForgeTypes.h file if needed"""
        # Check if NetForgeTypes.h exists
        types_header_path = None
        for module_dir in self.source_dir.iterdir():
            if module_dir.is_dir():
                potential_path = module_dir / "Public" / "NetForgeTypes.h"
                if potential_path.exists():
                    types_header_path = potential_path
                    break
        
        if types_header_path:
            logger.info(f"NetForgeTypes.h already exists at {types_header_path}")
            return False
        
        # Find module name
        module_name = None
        for module_dir in self.source_dir.iterdir():
            if module_dir.is_dir() and (module_dir / "Public").exists() and (module_dir / "Private").exists():
                module_name = module_dir.name
                types_header_path = module_dir / "Public" / "NetForgeTypes.h"
                break
        
        if not module_name:
            logger.error("Could not determine module name")
            return False
        
                # Create NetForgeTypes.h
        os.makedirs(types_header_path.parent, exist_ok=True)
        
        with open(types_header_path, 'w', encoding='utf-8') as f:
            f.write(f"""// NetForgeTypes.h - Common types for NetForge plugin
#pragma once

#include "CoreMinimal.h"
#include "NetForgeTypes.generated.h"

// Forward declarations
class UNetForgeSessionManager;

UENUM(BlueprintType)
enum class ENetForgeSessionState : uint8
{{
    None,
    Creating,
    Searching,
    Joining,
    Active,
    Error
}};

USTRUCT(BlueprintType)
struct F{module_name.upper()}_API FNetForgeMetricsHistory
{{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "NetForge|Metrics")
    bool bCircuitOpen = false;

    // Add anomaly detection method
    bool IsAnomalyDetected() const {{ return false; }}
}};

USTRUCT(BlueprintType)
struct F{module_name.upper()}_API FNetForgeFinding
{{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "NetForge|Session")
    FString Name;
    
    UPROPERTY(BlueprintReadWrite, Category = "NetForge|Session")
    FString Description;
}};

// Define search presence constant
#define SEARCH_PRESENCE TEXT("SEARCH_PRESENCE")
""")
        
        logger.info(f"Created NetForgeTypes.h at {types_header_path}")
        return True

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python implementation_fixer.py <project_directory>")
        return
    
    project_dir = sys.argv[1]
    fixer = ImplementationFixer(project_dir)
    
    # Fix NetForgeTypes.h first if missing
    fixer.fix_netforge_types()
    
    # Find and fix implementation issues
    issues = fixer.find_implementation_issues()
    if issues:
        fixes_applied = fixer.fix_issues(issues)
        print(f"Applied {fixes_applied} fixes")
    else:
        print("No implementation issues found")

if __name__ == "__main__":
    main()