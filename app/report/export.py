from typing import List
from app.models.schemas import (
    ComparisonResult, DealVerdict, ComparisonFinding, CrossDocumentRisk,
    DisclosureIssue, PartySpecificRecommendation, CompanyRole, LegalCategory, Priority
)


def generate_html_report(result: ComparisonResult) -> str:
    verdict = result.verdict
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DISCLAI Transaction Report - {result.transaction_id}</title>
    <style>
        @page {{
            margin: 2cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }}
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a2b3d;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
        }}
        .report-header {{
            text-align: center;
            border-bottom: 3px solid #1a3c5e;
            padding-bottom: 30px;
            margin-bottom: 40px;
        }}
        .report-title {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a3c5e;
            margin-bottom: 10px;
        }}
        .report-subtitle {{
            font-size: 1.25rem;
            color: #4a5a6d;
        }}
        .report-meta {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            font-size: 0.9rem;
            color: #666;
        }}
        .section {{
            margin-bottom: 40px;
            page-break-inside: avoid;
        }}
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #1a3c5e;
            border-bottom: 2px solid #1a3c5e;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .subsection-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #2d5a8a;
            margin: 24px 0 12px;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        .card {{
            background: #f5f7fa;
            border: 1px solid #d0d8e0;
            border-radius: 8px;
            padding: 20px;
        }}
        .card-title {{
            font-weight: 600;
            margin-bottom: 12px;
            color: #1a2b3d;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e4e8;
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #4a5a6d; }}
        .stat-value {{ font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-critical {{ background: #fcecec; color: #7a1a1a; }}
        .badge-high {{ background: #fdf0e0; color: #a83232; }}
        .badge-medium {{ background: #fef9e7; color: #b8860b; }}
        .badge-low {{ background: #eafaf1; color: #2d7d4a; }}
        .badge-matched {{ background: #e8f4fa; color: #2a6b8a; }}
        .badge-partial {{ background: #fef9e7; color: #b8860b; }}
        .badge-unmatched {{ background: #fcecec; color: #a83232; }}
        .badge-review {{ background: #f0f0f0; color: #7a8a9d; }}
        .finding {{
            margin-bottom: 24px;
            padding: 20px;
            background: #fafbfc;
            border-radius: 8px;
            border-left: 4px solid #d0d8e0;
            page-break-inside: avoid;
        }}
        .finding.critical {{ border-left-color: #7a1a1a; }}
        .finding.high {{ border-left-color: #a83232; }}
        .finding.medium {{ border-left-color: #b8860b; }}
        .finding.low {{ border-left-color: #2d7d4a; }}
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .finding-title {{ font-weight: 600; font-size: 1.1rem; }}
        .finding-category {{ font-size: 0.85rem; color: #7a8a9d; }}
        .evidence-box {{
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.8rem;
            background: white;
            padding: 14px;
            border-radius: 6px;
            border: 1px solid #d0d8e0;
            margin-top: 12px;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }}
        .evidence-header {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #4a5a6d;
            font-family: inherit;
            font-size: 0.85rem;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 12px;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #d0d8e0;
        }}
        .comparison-table th {{
            background: #f5f7fa;
            font-weight: 600;
            color: #4a5a6d;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}
        .risk-item {{
            margin-bottom: 16px;
            padding: 16px;
            background: #fafbfc;
            border-radius: 8px;
            border-left: 4px solid #d0d8e0;
        }}
        .risk-item.critical {{ border-left-color: #7a1a1a; }}
        .risk-item.high {{ border-left-color: #a83232; }}
        .risk-item.medium {{ border-left-color: #b8860b; }}
        .risk-item.low {{ border-left-color: #2d7d4a; }}
        .risk-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .risk-title {{ font-weight: 600; }}
        .rec-item {{
            margin-bottom: 16px;
            padding: 16px;
            background: #fafbfc;
            border-radius: 8px;
            border-left: 4px solid #c8a840;
        }}
        .rec-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .rec-title {{ font-weight: 600; }}
        .methodology {{
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.75rem;
            background: #f5f7fa;
            padding: 16px;
            border-radius: 6px;
            white-space: pre-wrap;
            border: 1px solid #d0d8e0;
        }}
        .disclaimer {{
            margin-top: 40px;
            padding: 20px;
            background: #fef9e7;
            border: 1px solid #f5e0a0;
            border-radius: 8px;
            font-size: 0.85rem;
            color: #b8860b;
        }}
        @media print {{
            body {{ padding: 0; }}
            .section {{ page-break-inside: avoid; }}
            .finding, .risk-item, .rec-item {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1 class="report-title">DISCLAI Transaction Intelligence Report</h1>
        <p class="report-subtitle">{result.company_a_name} vs {result.company_b_name}</p>
        <div class="report-meta">
            <span><strong>Transaction:</strong> {result.transaction_id}</span>
            <span><strong>Comparison:</strong> {result.comparison_id[:8]}</span>
            <span><strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d')}</span>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Executive Summary</h2>
        <div class="grid-2">
            <div class="card">
                <div class="card-title">Overall Assessment</div>
                <p style="font-size: 1.1rem; margin-bottom: 16px;">{verdict.overall_assessment}</p>
                <div class="stat-row">
                    <span class="stat-label">Risk Level</span>
                    <span class="stat-value"><span class="badge badge-{verdict.overall_risk_level.value.lower()}">{verdict.overall_risk_level.value}</span></span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Deal Score</span>
                    <span class="stat-value">{verdict.score}/100</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Confidence</span>
                    <span class="stat-value">{"%.0f%%" % (verdict.confidence * 100)}</span>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Key Metrics</div>
                <div class="stat-row">
                    <span class="stat-label">Material Asymmetries</span>
                    <span class="stat-value">{verdict.material_asymmetries}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Critical Issues</span>
                    <span class="stat-value">{verdict.critical_issues}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Cross-Document Risks</span>
                    <span class="stat-value">{len(result.cross_document_risks)}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Disclosure Issues</span>
                    <span class="stat-value">{len(result.disclosure_issues)}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Evidence-Backed Findings</span>
                    <span class="stat-value">{verdict.evidence_backed_findings}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Party Positions</h2>
        <div class="grid-2">
            <div class="card">
                <div class="card-title">{result.company_a_name} ({result.company_a_role.value})</div>
                <h4 style="color: #2d7d4a; margin: 16px 0 8px;">Advantages</h4>
                {'<ul style="margin-left: 20px;">' + ''.join(f'<li>{adv}</li>' for adv in verdict.company_a_advantages) + '</ul>' if verdict.company_a_advantages else '<p style="color: #7a8a9d;">No significant advantages identified.</p>'}
                <h4 style="color: #a83232; margin: 16px 0 8px;">Weaknesses</h4>
                {'<ul style="margin-left: 20px;">' + ''.join(f'<li>{weak}</li>' for weak in verdict.company_a_weaknesses) + '</ul>' if verdict.company_a_weaknesses else '<p style="color: #7a8a9d;">No significant weaknesses identified.</p>'}
            </div>
            <div class="card">
                <div class="card-title">{result.company_b_name} ({result.company_b_role.value})</div>
                <h4 style="color: #2d7d4a; margin: 16px 0 8px;">Advantages</h4>
                {'<ul style="margin-left: 20px;">' + ''.join(f'<li>{adv}</li>' for adv in verdict.company_b_advantages) + '</ul>' if verdict.company_b_advantages else '<p style="color: #7a8a9d;">No significant advantages identified.</p>'}
                <h4 style="color: #a83232; margin: 16px 0 8px;">Weaknesses</h4>
                {'<ul style="margin-left: 20px;">' + ''.join(f'<li>{weak}</li>' for weak in verdict.company_b_weaknesses) + '</ul>' if verdict.company_b_weaknesses else '<p style="color: #7a8a9d;">No significant weaknesses identified.</p>'}
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Comparative Findings</h2>
"""
    
    for finding in result.findings:
        classification_lower = finding.classification.value.lower().replace('_', '-')
        html += f"""
        <div class="finding {classification_lower}">
            <div class="finding-header">
                <div>
                    <div class="finding-title">{finding.provision}</div>
                    <div class="finding-category">{finding.category.value}{' • ' + finding.subcategory if finding.subcategory else ''}</div>
                </div>
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <span class="badge badge-{classification_lower}">{finding.classification.value}</span>
                    {f'<span class="badge badge-info">{finding.beneficiary.value} Advantage</span>' if finding.beneficiary else ''}
                </div>
            </div>
            <div style="margin-bottom: 12px;">
                <strong>Classification Reason:</strong> {finding.classification_reason}
            </div>
"""
        
        if finding.differences:
            html += """
            <table class="comparison-table">
                <thead>
                    <tr><th>Attribute</th><th>Company A</th><th>Company B</th><th>Difference</th></tr>
                </thead>
                <tbody>
"""
            for diff in finding.differences:
                diff_str = ""
                if diff.difference and isinstance(diff.difference, dict) and diff.difference.get("difference_months") is not None:
                    diff_str = f"{abs(diff.difference['difference_months'])} months"
                elif diff.absolute_difference is not None and diff.absolute_difference > 0:
                    diff_str = str(diff.absolute_difference)
                else:
                    diff_str = str(diff.difference) if diff.difference else "—"
                
                html += f"""
                    <tr>
                        <td>{diff.attribute}</td>
                        <td>{diff.company_a_value or '—'}</td>
                        <td>{diff.company_b_value or '—'}</td>
                        <td>{diff_str}</td>
                    </tr>
"""
            html += "</tbody></table>"
        
        if finding.advantage_explanation:
            html += f'<div style="margin-top: 12px; padding: 12px; background: #e8f4fa; border-radius: 6px;"><strong>Advantage Analysis:</strong> {finding.advantage_explanation}</div>'
        
        html += f"""
            <div style="margin-top: 12px;">
                <strong>Legal Impact:</strong> {finding.legal_impact}
                {'<br><strong>Commercial Impact:</strong> ' + finding.commercial_impact if finding.commercial_impact else ''}
                {'<br><strong>Negotiation Impact:</strong> ' + finding.negotiation_impact if finding.negotiation_impact else ''}
            </div>
"""
        
        if finding.company_a_position:
            html += f"""
            <div class="evidence-header">Company A Evidence (p.{finding.company_a_position.evidence.page_number}, §{finding.company_a_position.evidence.section_number or finding.company_a_position.evidence.heading})</div>
            <div class="evidence-box">{finding.company_a_position.evidence.text}</div>
"""
        if finding.company_b_position:
            html += f"""
            <div class="evidence-header">Company B Evidence (p.{finding.company_b_position.evidence.page_number}, §{finding.company_b_position.evidence.section_number or finding.company_b_position.evidence.heading})</div>
            <div class="evidence-box">{finding.company_b_position.evidence.text}</div>
"""
        
        html += "</div>"
    
    html += """
    </div>

    <div class="section">
        <h2 class="section-title">Cross-Document Risks</h2>
"""
    
    if result.cross_document_risks:
        for risk in result.cross_document_risks:
            html += f"""
        <div class="risk-item {risk.severity.value.lower()}">
            <div class="risk-header">
                <span class="risk-title">{risk.risk_type}</span>
                <span class="badge badge-{risk.severity.value.lower()}">{risk.severity.value}</span>
            </div>
            <p><strong>Description:</strong> {risk.description}</p>
            <p><strong>Impact:</strong> {risk.impact}</p>
            <p style="font-size: 0.85rem; color: #7a8a9d;"><strong>Component Findings:</strong> {len(risk.component_findings)} | <strong>Confidence:</strong> {"%.0f%%" % (risk.confidence * 100)}</p>
        </div>
"""
    else:
        html += '<p style="color: #7a8a9d;">No cross-document risks identified.</p>'
    
    html += """
    </div>

    <div class="section">
        <h2 class="section-title">Disclosure Issues</h2>
"""
    
    if result.disclosure_issues:
        for issue in result.disclosure_issues:
            html += f"""
        <div class="risk-item {issue.severity.value.lower()}">
            <div class="risk-header">
                <span class="risk-title">{issue.issue_type}</span>
                <span class="badge badge-{issue.severity.value.lower()}">{issue.severity.value}</span>
            </div>
            <p>{issue.description}</p>
            <p style="font-size: 0.85rem; color: #7a8a9d;"><strong>Status:</strong> {issue.status} | <strong>Confidence:</strong> {"%.0f%%" % (issue.confidence * 100)}</p>
"""
            if issue.spa_requirement:
                html += f"""
            <div class="evidence-header">SPA Requirement: {issue.spa_requirement.provision_name} (p.{issue.spa_requirement.evidence.page_number})</div>
            <div class="evidence-box">{issue.spa_requirement.evidence.text}</div>
"""
            if issue.data_room_evidence:
                html += f"""
            <div class="evidence-header">Data Room Evidence (p.{issue.data_room_evidence.page_number})</div>
            <div class="evidence-box">{issue.data_room_evidence.text}</div>
"""
            if issue.disclosure_schedule_evidence:
                html += f"""
            <div class="evidence-header">Disclosure Schedule (p.{issue.disclosure_schedule_evidence.page_number})</div>
            <div class="evidence-box">{issue.disclosure_schedule_evidence.text}</div>
"""
            html += "</div>"
    else:
        html += '<p style="color: #7a8a9d;">No disclosure issues identified.</p>'
    
    html += """
    </div>

    <div class="section">
        <h2 class="section-title">Party-Specific Recommendations</h2>
        <div class="grid-2">
            <div>
                <h3 class="subsection-title" style="color: #c8a840;">{company_a_name} Recommendations</h3>
"""
    
    if verdict.company_a_recommendations:
        for rec in verdict.company_a_recommendations:
            html += f"""
                <div class="rec-item">
                    <div class="rec-header">
                        <span class="rec-title">{rec.title}</span>
                        <span class="badge badge-{rec.priority.value.lower()}">{rec.priority.value}</span>
                    </div>
                    <p>{rec.description}</p>
                    <p style="font-size: 0.85rem;"><strong>Current:</strong> {rec.current_position}</p>
                    <p style="font-size: 0.85rem;"><strong>Proposed:</strong> {rec.proposed_adjustment}</p>
                    <p style="font-size: 0.8rem; color: #7a8a9d;"><em>Rationale: {rec.rationale}</em></p>
                    <p style="font-size: 0.8rem; color: #7a8a9d;"><em>Trade-off: {rec.commercial_tradeoff}</em></p>
                </div>
"""
    else:
        html += '<p style="color: #7a8a9d;">No specific recommendations.</p>'
    
    html += f"""
            </div>
            <div>
                <h3 class="subsection-title" style="color: #1a3c5e;">{result.company_b_name} Recommendations</h3>
"""
    
    if verdict.company_b_recommendations:
        for rec in verdict.company_b_recommendations:
            html += f"""
                <div class="rec-item">
                    <div class="rec-header">
                        <span class="rec-title">{rec.title}</span>
                        <span class="badge badge-{rec.priority.value.lower()}">{rec.priority.value}</span>
                    </div>
                    <p>{rec.description}</p>
                    <p style="font-size: 0.85rem;"><strong>Current:</strong> {rec.current_position}</p>
                    <p style="font-size: 0.85rem;"><strong>Proposed:</strong> {rec.proposed_adjustment}</p>
                    <p style="font-size: 0.8rem; color: #7a8a9d;"><em>Rationale: {rec.rationale}</em></p>
                    <p style="font-size: 0.8rem; color: #7a8a9d;"><em>Trade-off: {rec.commercial_tradeoff}</em></p>
                </div>
"""
    else:
        html += '<p style="color: #7a8a9d;">No specific recommendations.</p>'
    
    html += f"""
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Deal Verdict</h2>
        <p style="font-size: 1.1rem; margin-bottom: 20px;">{verdict.overall_assessment}</p>
        
        <h3 class="subsection-title">Recommended Actions</h3>
        <ol style="margin-left: 20px;">
"""
    
    for action in verdict.recommended_actions:
        html += f"            <li>{action}</li>\n"
    
    html += """        </ol>
"""
    
    if verdict.unresolved_questions:
        html += """
        <h3 class="subsection-title">Unresolved Questions</h3>
        <ul style="margin-left: 20px;">
"""
        for q in verdict.unresolved_questions:
            html += f"            <li>{q}</li>\n"
        html += "        </ul>\n"
    
    html += f"""
        <h3 class="subsection-title">Scoring Methodology</h3>
        <div class="methodology">{verdict.score_methodology}</div>
    </div>

    <div class="disclaimer">
        <strong>Disclaimer:</strong> This report is generated by DISCLAI, an AI-powered legal intelligence system. 
        It is intended as a decision-support tool for M&A counsel and does not constitute legal advice. 
        All findings require verification by qualified legal professionals. 
        The system may not capture all relevant provisions or contextual nuances. 
        Evidence references are based on automated extraction and should be independently verified against source documents.
    </div>
</body>
</html>
"""
    return html


from datetime import datetime