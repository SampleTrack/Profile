from pyrogram import Client, filters
from pyrogram.types import Message
import os
import ast
from info import ADMINS

def extract_pyrogram_commands(repo_path="."):
    commands = set()

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=full_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                for decorator in node.decorator_list:
                                    if isinstance(decorator, ast.Call):
                                        if hasattr(decorator.func, "attr") and decorator.func.attr == "on_message":
                                            for arg in decorator.args:
                                                if isinstance(arg, ast.Call) and getattr(arg.func, 'attr', '') == 'command':
                                                    if arg.args:
                                                        for a in arg.args:
                                                            if isinstance(a, ast.Constant):
                                                                commands.add(a.value.lower())
                                                            elif isinstance(a, ast.List):
                                                                for elt in a.elts:
                                                                    if isinstance(elt, ast.Constant):
                                                                        commands.add(elt.value.lower())
                    except Exception as e:
                        print(f"Error reading {full_path}: {e}")
    
    return sorted(commands)


# ✅ Pyrogram Handler for /allcommands
@Client.on_message(filters.command("allcommandz") & filters.user(ADMINS))
async def show_all_commandz(client, message: Message):
    commands = extract_pyrogram_commands(".")  # Scans current repo folder
    if not commands:
        await message.reply_text("❌ No commands found in the repo.")
        return

    reply = "**🧾 All Available Commands (A to Z):**\n\n"
    reply += "\n".join([f"🔹 `{cmd}`" for cmd in commands])
    await message.reply_text(reply, quote=True)
