<?php
/* Языковой файл */
function lang( $str ) {
        $lang = array(
            "1" => "Неизвестный тип запроса",
            "2" => "Абонент не найден",
            "3" => "Ошибка в формате денежной суммы",
            "4" => "Неверный формат даты",
            "5" => "Доступ с данного IP не предусмотрен",
            "6" => "Найдено более одного плательщика. Уточните параметра поиска",
            "7" => "Дублирование платежа.",
            "99" => "Ошибка провайдера",
            "report" => "Теперь оплату услуги можно производить в любом отделении ПРИВАТ-БАНКА или с помощью Вашей платежной карты!"
        );
        
        $str = $lang[$str];
        if(in_array( $str, $lang )) return $str; else return false;
}


?>