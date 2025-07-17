def get_user_company_and_role(user):
    from .models import TeamMember, TeamCompany  # можно оставить, это безопасно

    # 1. Если пользователь владелец
    team_company = TeamCompany.objects.filter(created_by=user).first()
    if team_company:
        return team_company, 'owner'
    
    # 2. Если сотрудник или менеджер
    team_member = TeamMember.objects.filter(user=user).first()
    if team_member:
        return team_member.company, team_member.role  # 'manager' или 'worker'

    # 3. Если ничего не нашли
    return None, None


def get_company_code(user):
    # Импорт внутри функции — чтобы избежать циклической ошибки
    from .models import RegisteredCompany, TeamMember

    # 1. Владелец компании
    registered = RegisteredCompany.objects.filter(registered_by=user).first()
    if registered:
        return ''.join(filter(str.isdigit, registered.code))  # только цифры

    # 2. Участник команды
    team_member = TeamMember.objects.select_related('company__registered_company').filter(user=user).first()
    if team_member and team_member.company.registered_company:
        return ''.join(filter(str.isdigit, team_member.company.registered_company.code))

    return None

from django.db.models import Avg, Count


def get_user_rating_data(user):

    from .models import Review
    """
    Возвращает среднюю оценку и количество отзывов для target_user.
    """
    data = Review.objects.filter(target_user=user).aggregate(
        average_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    # Округляем до 1 знака после запятой, если есть отзывы
    average = round(data['average_rating'], 1) if data['average_rating'] else 0
    count = data['total_reviews']
    
    return average, count


