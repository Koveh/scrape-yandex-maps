import streamlit as st
import pandas as pd
import sqlite3
import os
import sys
import glob
import time
from src.scraper import YandexMapsScraper
from src.decorators import logger

def show_gallery(session_dir):
    """Displays a gallery of images for a given session directory."""
    if not os.path.exists(session_dir):
        st.warning("Session directory not found.")
        return

    place_dirs = sorted([d for d in os.listdir(session_dir) if os.path.isdir(os.path.join(session_dir, d))])
    
    # Load metadata (CSV) to get links and details
    csv_path = os.path.join(session_dir, "places_data.csv")
    places_meta = {}
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            # Create a dict keyed by some identifier, but since folder names contain index, we can try to match by index
            # Folder format: "001_Name"
            for _, row in df.iterrows():
                # We'll use a simple matching strategy or just store by ID if we can infer it
                # Let's just store the whole dataframe and filter by name matching roughly
                pass
        except:
            pass

    # Pagination controls
    items_per_page = 10
    total_places = len(place_dirs)
    
    if total_places == 0:
        st.info("No places found.")
        return

    # Session state key for pagination
    page_key = f"gallery_page_{os.path.basename(session_dir)}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
        
    # Calculate pages
    total_pages = (total_places + items_per_page - 1) // items_per_page
    current_page = st.session_state[page_key]
    
    # Slice places
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_places)
    current_places = place_dirs[start_idx:end_idx]
    
    st.write(f"Showing places {start_idx + 1}-{end_idx} of {total_places}")
    
    found_photos = False
    
    for place_dir in current_places:
        place_path = os.path.join(session_dir, place_dir)
        photos_dir = os.path.join(place_path, "photos")
        
        # Get metadata for this place
        # Try to find matching row in CSV
        place_info = None
        if os.path.exists(csv_path):
             try:
                # Extract index from folder name "001_Name" -> 1
                idx_str = place_dir.split('_')[0]
                if idx_str.isdigit():
                    idx = int(idx_str)
                    # Assuming CSV has 'id' column which matches our index logic (1-based)
                    matches = df[df['id'] == idx]
                    if not matches.empty:
                        place_info = matches.iloc[0]
             except:
                 pass

        if os.path.exists(photos_dir):
            photos = [os.path.join(photos_dir, f) for f in os.listdir(photos_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            
            if photos:
                found_photos = True
                display_name = place_dir.split('_', 1)[1] if '_' in place_dir else place_dir
                
                with st.expander(f"📸 {display_name} ({len(photos)} photos)", expanded=False):
                    # Display Metadata if available
                    if place_info is not None:
                        md_cols = st.columns([2, 1, 1])
                        with md_cols[0]:
                            st.markdown(f"**Address:** {place_info.get('address', 'N/A')}")
                            if 'website' in place_info and pd.notna(place_info['website']):
                                st.markdown(f"**Website:** [{place_info['website']}]({place_info['website']})")
                        with md_cols[1]:
                             st.markdown(f"**Rating:** ⭐ {place_info.get('rating', 'N/A')} ({place_info.get('reviews_count', 0)} reviews)")
                        with md_cols[2]:
                            if 'link' in place_info and pd.notna(place_info['link']):
                                st.markdown(f"[📍 View on Map]({place_info['link']})")
                        st.divider()

                    cols = st.columns(4)
                    for i, photo in enumerate(photos):
                        with cols[i % 4]:
                            st.image(photo, caption=os.path.basename(photo))
                            
    if not found_photos and current_places:
        st.info("No photos found for the places on this page.")

    # Pagination buttons
    if total_pages > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if current_page > 1:
                if st.button("Previous", key=f"prev_{page_key}"):
                    st.session_state[page_key] -= 1
                    st.rerun()
        with c3:
            if current_page < total_pages:
                if st.button("Next", key=f"next_{page_key}"):
                    st.session_state[page_key] += 1
                    st.rerun()

# Set page config
st.set_page_config(
    page_title="Yandex Maps Scraper",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Yandex Maps Scraper")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    city = st.text_input("Region/City", value="Moscow")
    query_term = st.text_input("Search Query", value="Coffee shop")
    
    max_results = st.number_input("Max Results", min_value=1, max_value=500, value=10)
    
    st.subheader("Options")
    scrape_photos = st.checkbox("Scrape Photos", value=True)
    if scrape_photos:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            photo_format = st.selectbox("Format", ["jpg", "webp", "png"], index=0)
        with col_p2:
            max_photos = st.number_input("Max Photos", min_value=1, max_value=50, value=5, help="Photos per place")
    else:
        photo_format = "jpg"
        max_photos = 0
        
    scrape_reviews = st.checkbox("Scrape Reviews", value=True)
    headless = st.checkbox("Headless Mode", value=True, help="Run browser in background")
    
    browser_type = st.selectbox("Browser", ["Chrome", "Firefox", "Edge", "Safari"], index=0, help="Select the browser to use for scraping.")
    
    st.divider()
    
    if st.button("Clear All Data", type="secondary"):
        st.session_state['confirm_clear'] = True

    if st.session_state.get('confirm_clear', False):
        st.warning("Are you sure you want to delete ALL data? This cannot be undone.", icon="⚠️")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Yes, Delete Everything", type="primary"):
                import shutil
                try:
                    if os.path.exists("output_data"):
                        shutil.rmtree("output_data")
                        os.makedirs("output_data")
                        st.toast("Data cleared!", icon="🗑️")
                        st.session_state['confirm_clear'] = False
                        st.rerun()
                except Exception as e:
                    st.error(f"Error clearing data: {e}")
        with col_c2:
            if st.button("Cancel", type="secondary"):
                st.session_state['confirm_clear'] = False
                st.rerun()
    
    start_btn = st.button("Start Scraping", type="primary")

# Main content area
if start_btn:
    # Handle multiple queries if needed
    # For now, let's treat query_term as comma-separated if user wants
    queries = [q.strip() for q in query_term.split(",")]
    
    status_container = st.container()
    
    all_session_dirs = []
    
    with st.spinner("Scraping in progress..."):
        # Run scraper for each query
        for q in queries:
            if not q: continue
            
            full_query = f"{q} {city}"
            st.info(f"Processing: **{full_query}**")
            
            try:
                # Initialize scraper
                scraper = YandexMapsScraper(
                    headless=headless,
                    max_results=max_results,
                    scrape_photos=scrape_photos,
                    scrape_reviews=scrape_reviews,
                    photo_format=photo_format,
                    max_photos=max_photos,
                    browser_type=browser_type
                )
                
                # Define progress callback
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total, message):
                    status_text.text(f"{message} ({current}/{total})")
                    if total > 0:
                        progress = min(current / total, 1.0)
                        progress_bar.progress(progress)
                
                scraper.on_progress = update_progress
                
                scraper.run(full_query)
                session_dir = scraper.data_manager.current_session_dir
                if session_dir:
                    all_session_dirs.append(session_dir)
                    
                # Clear progress after completion
                status_text.empty()
                progress_bar.empty()
                    
            except Exception as e:
                st.error(f"Error scraping {full_query}: {e}")
                
    if all_session_dirs:
        st.success("All tasks completed!")
        
        # We'll just show the LAST session for preview for simplicity, 
        # or we could merge them. Let's show the last one but list all.
        last_session = all_session_dirs[-1]
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Preview (Last Run)", "📥 Downloads", "📁 Files", "📸 Gallery"])
        
        with tab1:
            csv_file = os.path.join(last_session, "places_data.csv")
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                st.dataframe(df)
            else:
                st.warning("No CSV found for preview.")

        with tab2:
            st.write("Download results from the last session:")
            # ... existing download buttons logic for last_session ...
            csv_file = os.path.join(last_session, "places_data.csv")
            json_file = os.path.join(last_session, "places_data.json")
            sqlite_file = os.path.join(last_session, "places_data.db")
            xlsx_file = os.path.join(last_session, "places_data.xlsx")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if os.path.exists(csv_file):
                    with open(csv_file, "rb") as f:
                        st.download_button("Download CSV", f, f"maps_{city}_{q}.csv", "text/csv")
            with col2:
                if os.path.exists(json_file):
                    with open(json_file, "rb") as f:
                        st.download_button("Download JSON", f, f"maps_{city}_{q}.json", "application/json")
            with col3:
                if os.path.exists(sqlite_file):
                    with open(sqlite_file, "rb") as f:
                        st.download_button("Download DB", f, f"maps_{city}_{q}.db", "application/x-sqlite3")
            with col4:
                if os.path.exists(xlsx_file):
                    with open(xlsx_file, "rb") as f:
                        st.download_button("Download Excel", f, f"maps_{city}_{q}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with tab3:
            st.write("Created Sessions:")
            for s in all_session_dirs:
                st.code(s)
                
        with tab4:
            show_gallery(last_session)

else:
    # Show previous results if any
    st.subheader("Previous Sessions")
    base_dir = "output_data"
    if os.path.exists(base_dir):
        # List directories sorted by time
        sessions = sorted(glob.glob(os.path.join(base_dir, "*")), key=os.path.getmtime, reverse=True)
        
        if sessions:
            selected_session = st.selectbox("Select a past session to view", sessions, format_func=lambda x: os.path.basename(x))
            
            if selected_session:
                tab_hist_1, tab_hist_2, tab_hist_3 = st.tabs(["📊 Data", "📥 Downloads", "📸 Gallery"])
                
                csv_file = os.path.join(selected_session, "places_data.csv")
                sqlite_file = os.path.join(selected_session, "places_data.db")
                xlsx_file = os.path.join(selected_session, "places_data.xlsx")
                
                with tab_hist_1:
                    if os.path.exists(csv_file):
                        df = pd.read_csv(csv_file)
                        st.dataframe(df)
                    elif os.path.exists(sqlite_file):
                        try:
                            conn = sqlite3.connect(sqlite_file)
                            df = pd.read_sql_query("SELECT * FROM places", conn)
                            conn.close()
                            st.dataframe(df)
                        except:
                            st.write("Could not read DB")
                    else:
                        st.info("No data files in this session.")
                
                with tab_hist_2:
                    col1, col2 = st.columns(2)
                    with col1:
                        if os.path.exists(csv_file):
                            with open(csv_file, "rb") as f:
                                st.download_button(
                                    label="Download CSV",
                                    data=f,
                                    file_name=os.path.basename(selected_session) + ".csv",
                                    mime="text/csv",
                                    key="download_prev_csv"
                                )
                    with col2:
                        if os.path.exists(xlsx_file):
                            with open(xlsx_file, "rb") as f:
                                st.download_button(
                                    label="Download Excel",
                                    data=f,
                                    file_name=os.path.basename(selected_session) + ".xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_prev_xlsx"
                                )

                with tab_hist_3:
                    show_gallery(selected_session)
        else:
            st.info("No previous sessions found.")
