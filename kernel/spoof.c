#include <linux/init.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/cred.h>
#include <linux/spinlock.h>
#include <linux/spoof.h>

static DEFINE_SPINLOCK(spoof_lock);

struct spoof_config g_spoof_config = {
	.baseband = "15081906",
	.board = "blazer",
	.hardware = "powervr",
	.bootloader = "15081906",
	.build_date_utc = "1774400006000",
	.build_date = "Wed Mar 25 00:53:26 2026 ",
	.kernel_release = "6.6.102-android15-8-g6eb5b2a8c46b-ab14739656-4k",
	.cpu_name = "",
};

const char *get_spoof_baseband(void)
{
	return g_spoof_config.baseband;
}
EXPORT_SYMBOL(get_spoof_baseband);

const char *get_spoof_board(void)
{
	return g_spoof_config.board;
}
EXPORT_SYMBOL(get_spoof_board);

const char *get_spoof_hardware(void)
{
	return g_spoof_config.hardware;
}
EXPORT_SYMBOL(get_spoof_hardware);

const char *get_spoof_bootloader(void)
{
	return g_spoof_config.bootloader;
}
EXPORT_SYMBOL(get_spoof_bootloader);

const char *get_spoof_build_date_utc(void)
{
	return g_spoof_config.build_date_utc;
}
EXPORT_SYMBOL(get_spoof_build_date_utc);

const char *get_spoof_build_date(void)
{
	return g_spoof_config.build_date;
}
EXPORT_SYMBOL(get_spoof_build_date);

const char *get_spoof_kernel_release(void)
{
	return g_spoof_config.kernel_release;
}
EXPORT_SYMBOL(get_spoof_kernel_release);

const char *get_spoof_cpu_name(void)
{
	return g_spoof_config.cpu_name;
}
EXPORT_SYMBOL(get_spoof_cpu_name);

static int spoof_config_show(struct seq_file *m, void *v)
{
	unsigned long flags;

	spin_lock_irqsave(&spoof_lock, flags);
	seq_printf(m, "baseband=%s\n", g_spoof_config.baseband);
	seq_printf(m, "board=%s\n", g_spoof_config.board);
	seq_printf(m, "hardware=%s\n", g_spoof_config.hardware);
	seq_printf(m, "bootloader=%s\n", g_spoof_config.bootloader);
	seq_printf(m, "build_date_utc=%s\n", g_spoof_config.build_date_utc);
	seq_printf(m, "build_date=%s\n", g_spoof_config.build_date);
	seq_printf(m, "kernel_release=%s\n", g_spoof_config.kernel_release);
	seq_printf(m, "cpu_name=%s\n", g_spoof_config.cpu_name);
	spin_unlock_irqrestore(&spoof_lock, flags);

	return 0;
}

static int spoof_config_open(struct inode *inode, struct file *file)
{
	/* 隐匿防护：只有 root 进程 (UID 0) 允许打开与访问，对普通探测应用隐匿并返回 ENOENT */
	if (current_uid().val != 0)
		return -ENOENT;

	return single_open(file, spoof_config_show, NULL);
}

static ssize_t spoof_config_write(struct file *file, const char __user *buf,
				  size_t count, loff_t *ppos)
{
	char *kbuf, *line, *p;
	unsigned long flags;
	bool updated_cmdline = false;

	if (current_uid().val != 0)
		return -ENOENT;

	if (count > 4096)
		return -EINVAL;

	kbuf = memdup_user_nul(buf, count);
	if (IS_ERR(kbuf))
		return PTR_ERR(kbuf);

	spin_lock_irqsave(&spoof_lock, flags);
	p = kbuf;
	while ((line = strsep(&p, "\r\n")) != NULL) {
		char *eq, *key, *val;

		line = strim(line);
		if (*line == '\0' || *line == '#')
			continue;

		eq = strchr(line, '=');
		if (!eq)
			continue;

		*eq = '\0';
		key = strim(line);
		val = strim(eq + 1);

		if (!strcmp(key, "baseband")) {
			strlcpy(g_spoof_config.baseband, val, sizeof(g_spoof_config.baseband));
			updated_cmdline = true;
		} else if (!strcmp(key, "board")) {
			strlcpy(g_spoof_config.board, val, sizeof(g_spoof_config.board));
		} else if (!strcmp(key, "hardware")) {
			strlcpy(g_spoof_config.hardware, val, sizeof(g_spoof_config.hardware));
			updated_cmdline = true;
		} else if (!strcmp(key, "bootloader")) {
			strlcpy(g_spoof_config.bootloader, val, sizeof(g_spoof_config.bootloader));
			updated_cmdline = true;
		} else if (!strcmp(key, "build_date_utc")) {
			strlcpy(g_spoof_config.build_date_utc, val, sizeof(g_spoof_config.build_date_utc));
		} else if (!strcmp(key, "build_date")) {
			strlcpy(g_spoof_config.build_date, val, sizeof(g_spoof_config.build_date));
		} else if (!strcmp(key, "kernel_release")) {
			strlcpy(g_spoof_config.kernel_release, val, sizeof(g_spoof_config.kernel_release));
		} else if (!strcmp(key, "cpu_name")) {
			strlcpy(g_spoof_config.cpu_name, val, sizeof(g_spoof_config.cpu_name));
		}
	}
	spin_unlock_irqrestore(&spoof_lock, flags);

	kfree(kbuf);

	if (updated_cmdline)
		update_spoof_cmdline();

	return count;
}

static const struct file_operations spoof_config_fops = {
	.open		= spoof_config_open,
	.read		= seq_read,
	.write		= spoof_config_write,
	.llseek		= seq_lseek,
	.release	= single_release,
};

static int __init spoof_init(void)
{
	struct proc_dir_entry *entry;

	entry = proc_create("spoof_config", 0600, NULL, &spoof_config_fops);
	if (!entry)
		pr_err("spoof: failed to create /proc/spoof_config\n");
	else
		pr_info("spoof: dynamic spoof controller initialized\n");

	return 0;
}
late_initcall(spoof_init);
