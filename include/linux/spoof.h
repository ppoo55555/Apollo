#ifndef _LINUX_SPOOF_H
#define _LINUX_SPOOF_H

#include <linux/types.h>

struct spoof_config {
	char baseband[64];
	char board[64];
	char hardware[64];
	char bootloader[64];
	char build_date_utc[64];
	char build_date[128];
	char kernel_release[64];
	char cpu_name[128];
};

extern struct spoof_config g_spoof_config;

const char *get_spoof_baseband(void);
const char *get_spoof_board(void);
const char *get_spoof_hardware(void);
const char *get_spoof_bootloader(void);
const char *get_spoof_build_date_utc(void);
const char *get_spoof_build_date(void);
const char *get_spoof_kernel_release(void);
const char *get_spoof_cpu_name(void);

void update_spoof_cmdline(void);

#endif /* _LINUX_SPOOF_H */
