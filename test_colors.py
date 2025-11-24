import plotly.graph_objects as go

# Test colorscale
fig = go.Figure()

# Test points with known strengths
x_vals = [1, 2, 3]
y_vals = [100, 100, 100]
strengths = [3, 18, 100]  # Wave-19 (3), Wave -91 (18), Max (100)

fig.add_trace(go.Scatter(
    x=x_vals,
    y=y_vals,
    mode='markers',
    marker=dict(
        size=30,
        color=strengths,
        colorscale='RdYlGn',  # 0=Red, 100=Green
        cmin=0,
        cmax=100,
        showscale=True,
    ),
    text=[f'Strength={s}' for s in strengths],
    textposition='bottom center',
))

fig.update_layout(
    title='Color Test: Strength 3 (should be RED), 18 (should be RED/ORANGE), 100 (should be GREEN)',
    xaxis=dict(title='Point Number'),
    yaxis=dict(range=[90, 110]),
)

fig.write_html('charts/color_test.html')
print("Created charts/color_test.html")
print("Point 1 (strength=3): should be DARK RED")
print("Point 2 (strength=18): should be LIGHT RED/ORANGE")  
print("Point 3 (strength=100): should be GREEN")
