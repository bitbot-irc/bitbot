from src import EventManager, ModuleManager, utils
from . import types

# describing command arg specifications, to centralise parsing and validating.
#
# format: <!|?><name>
#   ! = required
#   ? = optional
#
# if "name" contains "~", it will be marked as an "important" spec
# this means that, e.g. "!r~channel" will be:
#   - marked as important
#   - name split to everything after ~
#   - the name, and it's value, will be offered to other preprocessors.
#
# this means, in practice, that "!r~channel" is a:
#   - "revelant" channel (current if in channel, explicit arg otherwise)
#   - will be used to check if a user has permissions
#
# spec types:
#   - "time" - +1w2d3h4m5s format time
#   - "rchannel" - relevant channel. current channel if we're in channel,
#     otherwise an explicit channel name argument
#   - "channel" - an argument of a channel name
#   - "cuser" - a nickname but only if they are in the current channel
#   - "ruser" - revlevant user. either current user if no arguments, otherwise
#     take nickname for user from given args
#   - "user" - an argument of a user's nickname
#   - "ouser" - an argument of a potentially offline user's nickname
#   - "word" - one word from arguments
#   - "string" - collect all remaining args in to a string

class Module(ModuleManager.BaseModule):
    def _spec_value(self, server, channel, user, argument_types, args):
        options = []
        first_error = None
        for argument_type in argument_types:
            value = None
            n = 0
            error = None

            simple_value, simple_count = argument_type.simple(args)
            if not simple_count == -1:
                value = simple_value
                n = simple_count
                error = argument_type.error()
            else:
                if argument_type.type in types.TYPES:
                    func = types.TYPES[argument_type.type]
                else:
                    func = self.exports.get_one(
                        "command-spec.%s" % argument_type.type)

                if func:
                    try:
                        value, n = func(server, channel, user, args)
                    except utils.parse.SpecTypeError as e:
                        error = e.message

            options.append([argument_type, value, n, error])
        return options

    def _argument_types(self, options, args):
        errors = []
        current_error = first_error = None
        for argument_type, value, n, error in options:
            if not value == None:
                return [argument_type, n, value]
            elif error:
                errors.append(error)
            elif n > len(args):
                errors.append("Not enough arguments")

        return [None, -1,
            errors[0] if len(errors) == 1 else "Invalid arguments"]

    @utils.hook("preprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess(self, event):
        specs = event["hook"].get_kwargs("spec")
        if specs:
            server = event["server"]
            channel = event["target"] if event["is_channel"] else None
            user = event["user"]

            overall_error = None
            best_count = 0
            for spec_arguments in specs:
                out = {}
                args = event["args_split"].copy()
                kwargs = {"channel": channel}
                failed = False

                current_error = None
                count = 0
                spec_index = 0
                for spec_argument in spec_arguments:
                    argument_type_multi = len(set(
                        t.type for t in spec_argument.types)) > 1
                    options = self._spec_value(server, kwargs["channel"], user,
                        spec_argument.types, args)

                    argument_type, n, value = self._argument_types(options, args)
                    if n > -1:
                        args = args[n:]

                        if argument_type.exported:
                            kwargs[argument_type.exported] = value

                        if argument_type_multi:
                            value = [argument_type.type, value]

                    elif not spec_argument.optional:
                        failed = True
                        current_error = value
                        break
                    else:
                        value = None

                    count += 1
                    if spec_argument.consume:
                        out[spec_index] = value
                        spec_index += 1
                        if argument_type:
                            key = argument_type.name() or argument_type.type
                            out[key] = value

                if not failed:
                    kwargs["spec"] = out
                    event["kwargs"].update(kwargs)
                    return
                else:
                    if count >= best_count:
                        overall_error = current_error

            error_out = overall_error

            if event["is_channel"]:
                context = utils.parse.SpecArgumentContext.CHANNEL
            else:
                context = utils.parse.SpecArgumentContext.PRIVATE
            usages = [
                utils.parse.argument_spec_human(s, context) for s in specs]
            command = "%s%s" % (event["command_prefix"], event["command"])
            usages = ["%s%s" % (command, u) for u in usages]

            error_out = "%s (Usage: %s)" % (overall_error, " | ".join(usages))

            return utils.consts.PERMISSION_HARD_FAIL, error_out
