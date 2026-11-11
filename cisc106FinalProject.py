from dataclasses import dataclass, field
from io import BytesIO
from drafter import *
import pandas as pd


@dataclass
class Calculation:
    """Stores the metadata and result of an individual statistical calculation."""

    column_name: str
    calculation_type: str
    result: float  # Supports decimal outputs accurately (e.g., standard deviation/mean)


@dataclass
class State:
    """Manages the application state, ensuring at least 4 fields are modified dynamically."""

    data_dict: dict = field(
        default_factory=dict
    )  # Field 1: Holds dataframe columns/values
    columns: list[str] = field(
        default_factory=list
    )  # Field 2: Holds list of discovered column names
    calculations_history: list[Calculation] = field(
        default_factory=list
    )  # Field 3: List of class instances
    history_search_query: str = (
        ""  # Field 4: State for search matching inside History page
    )


# ==========================================
# 1. HOME ROUTE
# ==========================================
@route
def index(state: State) -> Page:
    """Displays the home page with a welcome title and clear navigation paths."""
    return Page(
        state,
        [
            Text("📊 Statistical CSV Analyzer", style="heading"),
            Text(
                "Welcome! You can upload a CSV file to compute various metrics or view past records."
            ),
            HorizontalRule(),  # Fixed Component Name
            Button("Go to File Upload 📂", go_to_upload),
            Button("View Calculation History 📜", history_page),
        ],
    )


# ==========================================
# 2. INPUT ROUTE & PAGE
# ==========================================
@route
def go_to_upload(state: State) -> Page:
    """Input Page: Prompts the user to select and submit a CSV file."""
    return Page(
        state,
        [
            Text("Step 1: Upload Data Source", style="heading"),
            Text("Upload a raw CSV file from your device:"),
            FileUpload("csv_file"),
            Button("Upload File", upload_csv),
            Button("Back to Home", index),
        ],
    )


@route
def upload_csv(state: State, csv_file: dict) -> Page:
    """Processes raw bytes into a working dictionary format, cleaning state fields dynamically."""
    if not csv_file or not csv_file["content"]:
        return Page(
            state, [Text("⚠️ No file uploaded. Please go back and select a valid CSV.")]
        )

    # Convert bytes input to Pandas DataFrame
    data = pd.read_csv(BytesIO(csv_file["content"]))

    # Meaningfully modify State Fields 1 and 2
    state.data_dict = data.to_dict(orient="list")
    state.columns = list(data.columns)

    return go_to_calculate(state)


# ==========================================
# 3. CALCULATE ROUTE & PAGE
# ==========================================
@route
def go_to_calculate(state: State) -> Page:
    """Calculate Page: Offers target column selection and a menu of metric functions."""
    # List of required calculations
    calc_options = ["Mean", "Median", "Mode", "Standard Deviation", "Range", "IQR"]

    return Page(
        state,
        [
            Text("Step 2: Setup Your Analytics", style="heading"),
            Text(
                "Select a target column and choose which descriptive statistic to execute:"
            ),
            # Input fields (SelectBox)
            Text("Choose Column:"),
            SelectBox("column", state.columns),
            Text("Choose Calculation Type:"),
            SelectBox("calc_type", calc_options),
            Button("Run Analytical Model", execute_calculation),
            Button("Upload Different File", go_to_upload),
        ],
    )


# ==========================================
# 4. EXECUTION & RESULT ROUTE
# ==========================================
@route
def execute_calculation(state: State, column: str, calc_type: str) -> Page:
    """Computes targeted statistical operations, dynamically updates histories, and outputs results."""
    # Coerce structural lists back to numeric pandas types
    values = pd.to_numeric(pd.Series(state.data_dict[column]), errors="coerce")
    values = values.dropna()

    # Statement 1: Ensure dataset isn't completely empty after parsing
    if values.empty:
        return Page(
            state,
            [
                Text("⚠️ Error: Selected column has no valid numerical inputs."),
                Button("Back to Calculation Menu", go_to_calculate),
            ],
        )

    # Route matching algorithms to calculate specified values
    ans_value = 0.0

    if calc_type == "Mean":
        ans_value = values.mean()
    elif calc_type == "Median":
        ans_value = values.median()
    elif calc_type == "Mode":
        # Statement 2: Fallback configuration if mode returns multiple or empty elements
        mode_res = values.mode()
        ans_value = mode_res.iloc[0] if not mode_res.empty else 0.0
    elif calc_type == "Standard Deviation":
        ans_value = values.std()
    elif calc_type == "Range":
        ans_value = values.max() - values.min()
    elif calc_type == "IQR":
        # Interquartile Range evaluation via quantile distributions
        q3, q1 = values.quantile(0.75), values.quantile(0.25)
        ans_value = q3 - q1

    # Round clean answer value
    rounded_res = round(float(ans_value), 2)

    # Dynamic Instantiation: Generate a class instance and add to history
    new_calc = Calculation(
        column_name=column, calculation_type=calc_type, result=rounded_res
    )
    state.calculations_history.append(new_calc)  # Meaningfully modify Field 3

    # Direct transfer step into display-only route
    return show_results(state, new_calc)


@route
def show_results(state: State, active_calc: Calculation) -> Page:
    """Result Page: Confirms processing metrics with paths to run more calculations or exit."""
    display_str = (
        f"The {active_calc.calculation_type} of '{active_calc.column_name}' "
        f"is evaluated to: **{active_calc.result}**"
    )

    return Page(
        state,
        [
            Text("🎯 Calculation Result", style="heading"),
            Text(display_str),
            HorizontalRule(),  # Fixed Component Name
            Button("Run Another Calculation on data", go_to_calculate),
            Button("View History Records", history_page),
            Button("Return to Home Page", index),
        ],
    )


# ==========================================
# 5. HISTORY ROUTES & PAGE
# ==========================================
@route
def history_page(state: State) -> Page:
    """History Page: Renders dynamic summaries, executing sequential filtering loops."""
    output_view = [
        Text("📜 Master Calculations Logs", style="heading"),
        Text(
            "Search history logs by column name (Leave completely empty to view all records):"
        ),
        # Input Field: TextBox for search parameters
        TextBox("search_field", value=state.history_search_query),
        Button("Apply Search Filter", apply_history_filter),
        HorizontalRule(),  # Fixed Component Name
    ]

    query = state.history_search_query.strip().lower()
    has_results = False

    # Loop: Interrogates attributes within class instances dynamically
    for calc_record in state.calculations_history:
        # Statement 3: Selectively prints elements matching criteria
        if query == "" or query in calc_record.column_name.lower():
            has_results = True
            log_item = (
                f"▪️ Column: **{calc_record.column_name}** | "
                f"Metric: *{calc_record.calculation_type}* | "
                f"Result: {calc_record.result}"
            )
            output_view.append(Text(log_item))

    if not has_results:
        output_view.append(Text("No computational logs found matching that column."))

    output_view.append(HorizontalRule())  # Fixed Component Name
    output_view.append(Button("Back to Home Menu", index))

    return Page(state, output_view)


@route
def apply_history_filter(state: State, search_field: str) -> Page:
    """Intercepts, cleans, and updates State Field 4 to refresh filtered data structures."""
    state.history_search_query = search_field  # Meaningfully modify Field 4
    return history_page(state)


# Initialize system architecture with explicit empty state templates
start_server(State())
