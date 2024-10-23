## Download the balance sheet as a PDF

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from uuid import UUID
from helpers.utils import get_users, get_expenses, get_splits, calculate_user_expense_details

router = APIRouter()
@router.get("/balance-sheet/download/u/{user_id}")
async def download_balance_sheet(user_id: UUID):
    try:
        users = get_users()
        expenses = get_expenses().data
        splits = get_splits().data
        
        paid, owed, balances_by_user = calculate_user_expense_details(expenses, splits, user_id)

        # Create a PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']

        # Content elements in a balance sheet
        elements = []

        # Default sections
        elements.append(Paragraph(f"Expense Balance Sheet", title_style))
        elements.append(Paragraph(f"User: {users[str(user_id)]}", subtitle_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", normal_style))
        elements.append(Spacer(1, 20))

        # The user's summary
        elements.append(Paragraph("Your Summary", subtitle_style))
        summary_data = [
            ["Total Paid", f"Rs. {paid:.2f}"],
            ["Total Owed", f"Rs. {owed:.2f}"],
            ["Net Balance", f"Rs. {paid - owed:.2f}"]
        ]
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # User expenses section
        elements.append(Paragraph("Your Expenses", subtitle_style))
        user_expenses = []
        headers = ["Date", "Description", "Amount", "Split Type", "Participants"]
        user_expenses.append(headers)
        
        for expense in sorted(expenses, key=lambda x: x['created_at'], reverse=True):
            if expense['created_by'] == str(user_id):
                expense_splits = [s for s in splits if s['expense_id'] == expense['id']]
                participants = ", ".join([users[split['user_id']] for split in expense_splits])
                user_expenses.append([
                    datetime.fromisoformat(expense['created_at']).strftime('%Y-%m-%d'),
                    expense['name'],
                    f"Rs. {expense['amount']:.2f}",
                    expense['split_type'],
                    participants
                ])

        if len(user_expenses) > 1:  # If there are expenses for the user
            expenses_table = Table(user_expenses, colWidths=[1*inch, 2*inch, 1*inch, 1*inch, 2*inch])
            expenses_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(expenses_table)
        else:
            elements.append(Paragraph("No expenses created by you", normal_style))
        
        elements.append(Spacer(1, 20))

        # All expenses section
        elements.append(Paragraph("Overall Group Expenses", subtitle_style))
        all_expenses = []
        headers = ["Paid By", "Description", "Amount", "Split Type", "Your Share"]
        all_expenses.append(headers)

        for expense in sorted(expenses, key=lambda x: x['created_at'], reverse=True):
            if expense['created_by'] != str(user_id):  # show others' expenses
                expense_splits = [s for s in splits if s['expense_id'] == expense['id']]
                user_split = next((s for s in expense_splits if s['user_id'] == str(user_id)), None)
                if user_split:
                    all_expenses.append([
                        users[expense['created_by']],
                        expense['name'],
                        f"Rs. {expense['amount']:.2f}",
                        expense['split_type'],
                        f"Rs. {user_split['amount']:.2f}"
                    ])

        if len(all_expenses) > 1:  # If there are expenses
            overall_table = Table(all_expenses, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1.5*inch])
            overall_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(overall_table)
        else:
            elements.append(Paragraph("No expenses from others", normal_style))


        doc.build(elements)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=balance_sheet_{users[str(user_id)]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error generating balance sheet PDF: {str(e)}"
        )