import os
import sys

print("Patching KernelSU-Next for Linux 4.9 and Android 13...")

# 1. Alias strscpy_pad to __strscpy_pad across KernelSU source files
for root, dirs, files in os.walk('KernelSU/kernel'):
    for f in files:
        if f.endswith(('.c', '.h')) and f != 'kernel_compat.h':
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                content = fp.read()
            if 'strscpy_pad' in content:
                content = content.replace('strscpy_pad', '__strscpy_pad')
                with open(p, 'w', encoding='utf-8') as fp:
                    fp.write(content)
                print(f'Patched strscpy_pad in {f}')

# 2. Add macro polyfill in kernel_compat.h for kernels < 4.14
with open('KernelSU/kernel/compat/kernel_compat.h', 'r', encoding='utf-8') as f:
    c = f.read()
target = '#endif\n}\n\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)'
patch = '#endif\n}\n\n#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 14, 222)\n#define strscpy_pad __strscpy_pad\n#endif\n\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)'
if target in c:
    c = c.replace(target, patch)
    with open('KernelSU/kernel/compat/kernel_compat.h', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Patched kernel_compat.h for strscpy_pad')

# 3. Allow pagefault in strncpy_from_user_nofault during execve
with open('KernelSU/kernel/compat/kernel_compat.c', 'r', encoding='utf-8') as f:
    cc = f.read()
old_pf = '\tset_fs(USER_DS);\n\tpagefault_disable();\n\tret = strncpy_from_user(dst, unsafe_addr, count);\n\tpagefault_enable();\n\tset_fs(old_fs);'
new_pf = '\tset_fs(USER_DS);\n\tret = strncpy_from_user(dst, unsafe_addr, count);\n\tset_fs(old_fs);'
if old_pf in cc:
    cc = cc.replace(old_pf, new_pf)
    with open('KernelSU/kernel/compat/kernel_compat.c', 'w', encoding='utf-8') as f:
        f.write(cc)
    print('Patched strncpy_from_user_nofault in kernel_compat.c')
else:
    print('WARNING: old_pf not found in kernel_compat.c')

# 4. Fix init.rc path matching for GSI / LineageOS / system-as-root
with open('KernelSU/kernel/runtime/ksud_integration.c', 'r', encoding='utf-8') as f:
    kc = f.read()
old_init = '''    if (!!strcmp(dpath, "/init.rc") && !!strcmp(dpath, "/system/etc/init/hw/init.rc")) {
        return false;
    }

    return true;'''
new_init = '''    if (!strstr(dpath, "init.rc")) {
        return false;
    }

    pr_info("vfs_read: matched init.rc at %s\\n", dpath);
    return true;'''
if old_init in kc:
    kc = kc.replace(old_init, new_init)
    with open('KernelSU/kernel/runtime/ksud_integration.c', 'w', encoding='utf-8') as f:
        f.write(kc)
    print('Patched ksud_integration.c init.rc matching')
else:
    print('WARNING: old_init not found in ksud_integration.c')

print("KernelSU-Next patching complete!")
