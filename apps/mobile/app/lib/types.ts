export type StudentSelfResponse = {
    id: string;
    user_id: string;
    batch_id: string;
    roll_number: string;
    mentor_id: string | null;
    class_teacher_id: string | null;
    enrollment_year: number;
    created_at: string;
    updated_at: string;
};

export type PlanAction = {
    id: string;
    type: string;
    description: string;
    status: string;
    created_at: string;
};

export type InterventionPlan = {
    id: string;
    case_id: string;
    status: string;
    created_by: string;
    created_at: string;
    updated_at: string;
};

export type StudentCaseResponse = {
    case_id: string;
    status: string;
    urgency_band: string;
    opened_at: string;
    current_plan: InterventionPlan | null;
    plan_actions: PlanAction[];
    next_step: string;
};

export type StudentDecisionRequest = {
    decision: 'ACCEPTED' | 'CUSTOMIZED' | 'DECLINED';
    plan_actions: PlanAction[] | null;
    reason: string | null;
};

export type StudentDecisionResponse = {
    case_id: string;
    student_decision: string;
    decided_at: string;
};
