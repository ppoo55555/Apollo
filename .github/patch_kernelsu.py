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

# 5. Upgrade UAPI version to 5 for KernelSU-Next v3.4.1
supercall_h = 'KernelSU/uapi/supercall.h'
if os.path.exists(supercall_h):
    with open(supercall_h, 'r', encoding='utf-8') as f:
        sc = f.read()
    if 'KERNEL_SU_UAPI_VERSION = 4;' in sc:
        sc = sc.replace('KERNEL_SU_UAPI_VERSION = 4;', 'KERNEL_SU_UAPI_VERSION = 5;')
        print('Upgraded KERNEL_SU_UAPI_VERSION to 5 in supercall.h')
    if 'EVENT_MODULE_MOUNTED = 3;' in sc and 'EVENT_SERVICES' not in sc:
        sc = sc.replace(
            'static const __u32 EVENT_MODULE_MOUNTED = 3;',
            'static const __u32 EVENT_MODULE_MOUNTED = 3;\nstatic const __u32 EVENT_SERVICES = 4;'
        )
        print('Added EVENT_SERVICES in supercall.h')
    with open(supercall_h, 'w', encoding='utf-8') as f:
        f.write(sc)

# 6. Add EVENT_SERVICES handling in dispatch.c
dispatch_c = 'KernelSU/kernel/supercall/dispatch.c'
if os.path.exists(dispatch_c):
    with open(dispatch_c, 'r', encoding='utf-8') as f:
        dc = f.read()
    if 'static int do_report_event(void __user *arg)' in dc and 'services_started' not in dc:
        dc = dc.replace(
            'static int do_report_event(void __user *arg)\n{\n',
            'static int do_report_event(void __user *arg)\n{\n\tstatic bool services_started = false;\n'
        )
        dc = dc.replace(
            'case EVENT_POST_FS_DATA: {\n\t\tstatic bool post_fs_data_lock = false;',
            'case EVENT_POST_FS_DATA: {\n\t\tstatic bool post_fs_data_lock = false;\n\t\tservices_started = false;'
        )
        services_case = '''\tcase EVENT_SERVICES: {
\t\tif (services_started) {
\t\t\tpr_info("services already started, skipping\\n");
\t\t\treturn 0;
\t\t}
\t\tservices_started = true;
\t\tpr_info("services triggered\\n");
\t\treturn 1;
\t}
\tdefault:'''
        dc = dc.replace('\tdefault:', services_case)
        print('Added EVENT_SERVICES handler in dispatch.c')
        with open(dispatch_c, 'w', encoding='utf-8') as f:
            f.write(dc)

print("KernelSU-Next patching complete!")
