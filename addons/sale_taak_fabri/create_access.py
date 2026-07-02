with open('security/ir.model.access.csv', 'w', newline='') as f:
    f.write('id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n')
    f.write('access_sale_task_generator_wizard_user,sale.task.generator.wizard.user,model_sale_task_generator_wizard,base.group_user,1,1,1,1') 