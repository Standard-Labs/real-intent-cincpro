import streamlit as st
import pandas as pd


# Define global variables for column mappings
COLUMN_MAPPINGS = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email_1": "Email",
    "email_2": "CC Email",
    "phone_1": "Cell Phone",
    "phone_2": "Home Phone",
    "phone_3": "Work Phone",
    "address": "Street Address",
    "city": "City",
    "state": "State",
    "zip_code": "Zip/Postal Code",
}


def main():
    st.title('Real Intent to CINCPro Converter')

    st.info("""
    Upload a CSV file. The app will convert your Real Intent CSV into a format that can be imported into CINCPro.
    """)

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    agent_assigned = st.text_input("(Optional) Enter an assigned agent.")
    st.write("This will assign the lead to the selected agent.")
    
    listing_agent = st.text_input("(Optional) Enter a listing agent.")
    st.write("This will assign the lead to the selected listing agent.")

    partner = st.text_input("(Optional) Enter a partner.")
    st.write("This will assign the lead to the selected partner.")
    
    pipeline = st.text_input("(Optional) Enter a pipeline.")
    st.write("This will set the lead’s pipeline stage. Note: this will not trigger any actions.")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Check if required columns are in the dataframe
        missing_columns = [col for col in COLUMN_MAPPINGS.keys() if col not in df.columns]
        
        if not missing_columns:

            df_cincpro = df[list(COLUMN_MAPPINGS.keys())].rename(columns=COLUMN_MAPPINGS)
            
            # add validation columns
            df_cincpro["Valid Email"] = df_cincpro["Email"].apply(lambda x: "YES" if pd.notna(x) and x != '' else "")
            df_cincpro["Valid Cell Phone"] = df_cincpro[["Cell Phone", "Home Phone", "Work Phone"]].apply(lambda x: "YES" if x.notna().any() else "", axis=1)


            if 'insight' in df.columns:
                df_cincpro['Custom Note'] = df['insight'].apply(lambda x: f"Insight: {x}")
                
            if agent_assigned:
                df_cincpro['Agent Assigned'] = agent_assigned
            if listing_agent:
                df_cincpro['Listing Agent'] = listing_agent
            if partner:
                df_cincpro['Partner'] = partner
            if pipeline:
                df_cincpro['Pipeline'] = pipeline

            df_cincpro['Source'] = 'Real Intent'
            

            # Display the resulting dataframe
            st.write("Converted DataFrame:")
            st.write(df_cincpro)
            
            # Download the converted dataframe as CSV
            csv = df_cincpro.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download converted CSV",
                data=csv,
                file_name='converted_file.csv',
                mime='text/csv',
            )
        else:
            st.write(f"The uploaded file does not contain the required columns: {', '.join(missing_columns)}.")


if __name__ == "__main__":
    main()