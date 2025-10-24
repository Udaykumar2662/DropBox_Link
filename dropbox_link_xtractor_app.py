import streamlit as st
import dropbox
import pandas as pd
import time
from dropbox.exceptions import ApiError

st.set_page_config(page_title="Dropbox Link Xtractor", page_icon="📦", layout="centered")

st.markdown(
    "<h2 style='text-align:center; color:#FF4B4B;'>📦 Dropbox Link Xtractor</h2>",
    unsafe_allow_html=True,
)

st.write("5 mins ka task yaar comensence use karo Gangadhar.")

# --- Input fields ---
api_key = st.text_input("🔑 Dropbox API Key", type="password", help="Paste your Dropbox API token here.")
folder_path = st.text_input("📁 Folder Path (e.g. /Joo boltha hu ho karo GANGU")
file_types = st.text_input("📄 File Types (comma separated, e.g. jpg,png,pdf)", "jpg,png,pdf")

generate = st.button("🚀 Lets do Kummudu")

def is_allowed(filename, extensions):
    return any(filename.lower().endswith(ext) for ext in extensions)

def get_or_create_shared_link(dbx, path):
    try:
        res = dbx.sharing_list_shared_links(path=path, direct_only=True)
        if res.links:
            url = res.links[0].url
        else:
            settings = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
            link = dbx.sharing_create_shared_link_with_settings(path, settings)
            url = link.url
        if "?dl=0" not in url and "?dl=1" not in url:
            url += "?dl=0"
        return url
    except Exception as e:
        st.error(f"Error creating link for {path}: {e}")
        return ""

if generate:
    if not api_key or not folder_path:
        st.warning("Please enter your API key and folder path.")
    else:
        try:
            dbx = dropbox.Dropbox(api_key)
            st.info("Here me Out Gangu")

            response = dbx.files_list_folder(folder_path, recursive=True)
            files = []
            extensions = [f".{e.strip().lower()}" for e in file_types.split(",")]

            while True:
                for entry in response.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if is_allowed(entry.name, extensions):
                            url = get_or_create_shared_link(dbx, entry.path_lower)
                            files.append({
                                "file_name": entry.name,
                                "dropbox_path": entry.path_display,
                                "shared_url": url
                            })
                            time.sleep(0.2)
                if response.has_more:
                    response = dbx.files_list_folder_continue(response.cursor)
                else:
                    break

            if not files:
                st.warning("I Did'nt Get it.")
            else:
                df = pd.DataFrame(files)
                output_file = "dropbox_links_output.xlsx"
                df.to_excel(output_file, index=False)

                st.success(f"✅ Successfully Fuc.....d")
                st.download_button(
                    label="📥 Download Excel File",
                    data=open(output_file, "rb").read(),
                    file_name=output_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except ApiError as e:
            st.error(f"Dropbox API Error: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
