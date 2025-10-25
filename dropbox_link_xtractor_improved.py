import streamlit as st
import dropbox
import pandas as pd
import time
from dropbox.exceptions import ApiError, AuthError

st.set_page_config(page_title="Dropbox Link Xtractor", page_icon="📦", layout="centered")

st.markdown("<h2 style='text-align: center; color: #FF4B4B;'>📦 Dropbox Link Xtractor</h2>", unsafe_allow_html=True)
st.write("Easily extract Dropbox file URLs into an Excel file.")

# Input fields
api_key = st.text_input("🔑 Dropbox API Key", type="password", help="Paste your Dropbox API token here.")
folder_path = st.text_input("📁 Folder Path (e.g., /Orange Tag Removed/Batch 4)")
file_types = st.text_input("📄 File Types (comma separated, e.g. jpg,png,pdf)", "jpg,png,pdf")

generate = st.button("🚀 Generate Dropbox Links")

def is_allowed(filename, extensions):
    """Check if file has allowed extension"""
    return any(filename.lower().endswith(ext.strip()) for ext in extensions)

def get_or_create_shared_link(dbx, path):
    """Get existing shared link or create new one"""
    try:
        res = dbx.sharing_list_shared_links(path=path, direct_only=True)
        if res.links:
            url = res.links[0].url
        else:
            settings = dropbox.sharing.SharedLinkSettings(
                requested_visibility=dropbox.sharing.RequestedVisibility.public
            )
            link = dbx.sharing_create_shared_link_with_settings(path, settings)
            url = link.url
        
        # Convert to direct download link
        direct_url = url.replace('www.dropbox.com', 'dl.dropboxusercontent.com').replace('?dl=0', '')
        return url, direct_url
    except ApiError as e:
        st.warning(f"Could not create link for {path}: {str(e)}")
        return None, None

if generate:
    if not api_key:
        st.error("❌ Please enter your Dropbox API Key")
    elif not folder_path:
        st.error("❌ Please enter a folder path")
    else:
        # Clean the API key (remove spaces)
        api_key_clean = api_key.strip()
        
        # Clean folder path
        if not folder_path.startswith('/'):
            folder_path = '/' + folder_path
        
        try:
            # Initialize Dropbox
            st.info("🔗 Connecting to Dropbox...")
            dbx = dropbox.Dropbox(api_key_clean)
            
            # Test the connection
            try:
                account = dbx.users_get_current_account()
                st.success(f"✅ Connected to Dropbox account: {account.name.display_name}")
            except AuthError as auth_err:
                st.error(f"❌ Authentication failed: {str(auth_err)}")
                st.error("Please check:")
                st.error("1. Token is copied correctly (no extra spaces)")
                st.error("2. Token has not expired")
                st.error("3. Token has correct permissions (files.metadata.read, files.content.read, sharing.write, sharing.read)")
                st.stop()
            
            # Parse file extensions
            extensions = [ext.strip().lower() for ext in file_types.split(',')]
            if not all(ext for ext in extensions):
                st.error("❌ Invalid file types format")
                st.stop()
            
            st.info(f"📂 Fetching file list from: {folder_path}")
            
            # List all files recursively
            result = dbx.files_list_folder(folder_path, recursive=True)
            all_entries = result.entries
            
            # Handle pagination
            while result.has_more:
                result = dbx.files_list_folder_continue(result.cursor)
                all_entries.extend(result.entries)
            
            # Filter files
            files_to_process = [
                entry for entry in all_entries
                if isinstance(entry, dropbox.files.FileMetadata) and is_allowed(entry.name, extensions)
            ]
            
            total_files = len(files_to_process)
            
            if total_files == 0:
                st.warning(f"⚠️ No files found with extensions: {', '.join(extensions)}")
            else:
                st.success(f"✅ Found {total_files} files. Generating links...")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                data = []
                
                for idx, entry in enumerate(files_to_process):
                    # Update progress
                    progress = (idx + 1) / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {idx + 1}/{total_files}: {entry.name}")
                    
                    # Get folder structure
                    path_parts = entry.path_display.split('/')
                    main_folder = path_parts[1] if len(path_parts) > 1 else ""
                    subfolder = path_parts[2] if len(path_parts) > 2 else ""
                    
                    # Get or create shared link
                    share_url, direct_url = get_or_create_shared_link(dbx, entry.path_display)
                    
                    if share_url:
                        data.append({
                            'Main Folder': main_folder,
                            'Subfolder': subfolder,
                            'File Name': entry.name,
                            'Dropbox Share Link': share_url,
                            'Direct Embed Link': direct_url
                        })
                    
                    # Rate limiting
                    time.sleep(0.1)
                
                progress_bar.empty()
                status_text.empty()
                
                if data:
                    # Create DataFrame
                    df = pd.DataFrame(data)
                    
                    # Create Excel file
                    output_file = 'dropbox_links.xlsx'
                    df.to_excel(output_file, index=False)
                    
                    st.success(f"✅ Successfully generated {len(data)} links!")
                    
                    # Show preview
                    st.subheader("📊 Preview (First 10 rows)")
                    st.dataframe(df.head(10))
                    
                    # Download button
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="⬇️ Download Excel File",
                            data=f,
                            file_name=output_file,
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                else:
                    st.warning("⚠️ No links were generated")
        
        except ApiError as e:
            st.error(f"❌ Dropbox API Error: {str(e)}")
            if "not_found" in str(e):
                st.error(f"The folder '{folder_path}' was not found in your Dropbox.")
                st.info("Please check the folder path and try again.")
        except AuthError as e:
            st.error(f"❌ Authentication Error: {str(e)}")
            st.error("Your access token is invalid or expired. Please generate a new one.")
        except Exception as e:
            st.error(f"❌ Something went wrong: {str(e)}")
