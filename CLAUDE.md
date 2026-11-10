# Notes for Claude Code

This repo is a setup guide for the Sharpa Wave W01 hand. To set up a machine, follow `README.md`
steps 1–7 in order. Verify each step before the next: `check_hand.sh`, `teleop.sh check`,
`cat /opt/sharpa-wave-sdk/VERSION`. Details are in `docs/`.

- **sudo:** you can't type the password, and `!` in Claude Code can't prompt for it. Ask the user to run
  🔑 commands in their own terminal, then verify the result yourself.
- **Physical steps are the user's:** cables, power, glove, Pilot clicks, calibration GUI. Give one short,
  concrete instruction at a time and wait. Users prefer short "do this now" steps over background.
- **Never move the hand without an explicit go-ahead.** That covers `first_move.py --move`,
  `/opt/sharpa-wave-sdk/sample/python/sharpa_wave_example.py` (full-range sweep, no prompt), and
  `teleop.sh wave` while Pilot is on GLOVE.
- **Don't run SDK code while Pilot is open.** This means `first_move.py` and anything that imports `sharpa`,
  because they share ports. `hand_status.py` only listens and is safe at any time.
- **The dongle is exclusive:** the client, the calibration GUI and `manus_pair` can't run together.
- **Terminals:** the client is an ncurses program. Let the user run it in a terminal. For an automated test,
  wrap it: `timeout -s INT 20 script -qfec "bash scripts/teleop.sh client" /dev/null`.
- **Ethernet:** if the PC has more than one wired interface, ask which one the hand is on
  (`setup_network.sh <iface>`).
- **Licensing:** `vendor/`, `calib/` and `logs/` hold licensed or personal files. They are gitignored. Never
  commit them or copy vendor code into the repo.
- Keep `README.md` short. Put details in `docs/`.
