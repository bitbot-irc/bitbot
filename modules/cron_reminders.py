from src import ModuleManager, utils

SETTING = "cron-reminders"

class Module(ModuleManager.BaseModule):
    _name = "cron"

    @utils.hook("cron")
    def cron(self, event):
        try:
            self._catch_cron(event["schedule"])
        except Exception as e:
            self.log.error("Failed to call cron reminders: %s", [str(e)],
                exc_info=True)
    def _catch_cron(self, schedule_check):
        all = []
        for server in self.bot.servers.values():
            channel_reminders = server.find_all_user_channel_settings(SETTING)
            for channel_name, nickname, value in channel_reminders:
                if channel_name in server.channels:
                    channel = server.channels.get(channel_name)
                    for schedule, text in value:
                        if schedule_check(schedule):
                            all.append([channel, nickname, text])

            user_reminders = server.get_all_user_settings(SETTING)
            for nickname, value in user_reminders:
                if server.has_user(nickname):
                    user = server.get_user(nickname)
                    for schedule, text in value:
                        if schedule_check(schedule):
                            all.append([user, user.nickname, text])

        for target, nickname, text in all:
            target.send_message("%s, reminder: %s" % (nickname, text))


    @utils.hook("received.command.cron")
    @utils.kwarg("permission", "cron")
    @utils.spec("!'add !<schedule>word !<reminder>string")
    @utils.spec("!'remove !<index>int")
    def command(self, event):
        user_id = event["user"].get_id()
        r = event["target"].get_user_setting(user_id, SETTING, [])

        if event["spec"][0] == "add":
            r.append([event["spec"][1].replace("+", " "), event["spec"][2]])
            event["stdout"].write("%s: added reminder"
                % event["user"].nickname)

        elif event["spec"][0] == "remove":
            if len(r) <= event["spec"][1]:
                raise utils.EventError("%s: invalid index (max %d)"
                    % (event["user"].nickname, len(r)-1))
            schedule, text = r.pop(event["spec"][1])
            event["stdout"].write("%s: removed reminder %d: %s (%s)"
                % (event["user"].nickname, event["spec"][1], schedule, text))

        event["target"].set_user_setting(user_id, SETTING, r)
